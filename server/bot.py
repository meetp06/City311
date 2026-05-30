#
# Copyright (c) 2024–2026, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Civora — Municipal 311 City Assistant voice bot (hackathon build).

Citizens call in to report potholes, broken streetlights, water leaks, graffiti,
abandoned vehicles, check trash schedules, ask about city policies, or escalate
to a human agent. All backend calls are mocked so the bot runs with no external
dependencies beyond the AI services.

Pipeline: Nemotron Speech Streaming STT → Nemotron-3-Super-120B LLM → Gradium TTS, with direct
function tools registered on the LLM context.

Run the bot using::

    uv run bot-nemotron.py
"""

import os
import random
from datetime import date

import aiohttp
from dotenv import load_dotenv
from loguru import logger
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import EndTaskFrame, FunctionCallResultProperties, LLMRunFrame, TranscriptionFrame, TextFrame, UserStartedSpeakingFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.runner.types import (
    RunnerArguments,
    SmallWebRTCRunnerArguments,
    WebSocketRunnerArguments,
)
from pipecat.runner.utils import parse_telephony_websocket
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.gradium.stt import GradiumSTTService
from pipecat.services.gradium.tts import GradiumTTSService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams, FastAPIWebsocketTransport
from pipecat.turns.user_turn_strategies import FilterIncompleteUserTurnStrategies
from pipecat.workers.runner import WorkerRunner

from mock_backend import (
    CITY_POLICIES,
    KNOWN_CALLERS,
    generate_ticket_id,
    lookup_trash_schedule,
)
from nemotron_llm import VLLMOpenAILLMService
from pipecat.transcriptions.language import Language

load_dotenv(override=True)


async def get_call_info(call_sid: str) -> dict:
    """Fetch call information from Twilio REST API using aiohttp.

    Args:
        call_sid: The Twilio call SID

    Returns:
        Dictionary containing call information including from_number, to_number, status, etc.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")

    if not account_sid or not auth_token:
        logger.warning("Missing Twilio credentials, cannot fetch call info")
        return {}

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls/{call_sid}.json"

    try:
        # Use HTTP Basic Auth with aiohttp
        auth = aiohttp.BasicAuth(account_sid, auth_token)

        async with aiohttp.ClientSession() as session:
            async with session.get(url, auth=auth) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Twilio API error ({response.status}): {error_text}")
                    return {}

                data = await response.json()

                call_info = {
                    "from_number": data.get("from"),
                    "to_number": data.get("to"),
                }

                return call_info

    except Exception as e:
        logger.error(f"Error fetching call info from Twilio: {e}")
        return {}


class DashboardNotifier(FrameProcessor):
    def __init__(self, send_event_fn):
        super().__init__()
        self.send_event = send_event_fn
        self.assistant_text_chunks = []

    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)

        # User finished speaking and transcription is finalized
        if isinstance(frame, TranscriptionFrame):
            if frame.text and frame.finalized:
                await self.flush_assistant_text()
                await self.send_event("transcript_added", {
                    "role": "citizen",
                    "text": frame.text
                })

        # LLM output chunk
        elif isinstance(frame, TextFrame):
            if frame.text:
                self.assistant_text_chunks.append(frame.text)

        # When a new user turn starts, the assistant has definitely finished speaking the previous turn
        elif isinstance(frame, UserStartedSpeakingFrame):
            await self.flush_assistant_text()

        # CRITICAL: forward every frame downstream so LLM->TTS audio reaches the
        # transport. Without this push_frame, the pipeline silently drops all
        # frames at this processor and the caller hears nothing.
        await self.push_frame(frame, direction)

    async def flush_assistant_text(self):
        if self.assistant_text_chunks:
            full_text = "".join(self.assistant_text_chunks).strip()
            self.assistant_text_chunks.clear()
            if full_text:
                await self.send_event("transcript_added", {
                    "role": "assistant",
                    "text": full_text
                })


async def run_bot(
    transport: BaseTransport,
    from_number: str | None = None,
    audio_in_sample_rate: int = 16000,
    audio_out_sample_rate: int = 24000,
    call_id: str | None = None,
):
    """Main bot logic.

    Args:
        transport: The transport to use.
        from_number: Caller's phone number (Twilio path only) for known-caller lookup.
        audio_in_sample_rate: Input audio sample rate in Hz. Defaults to 16000 (WebRTC).
        audio_out_sample_rate: Output audio sample rate in Hz. Defaults to 24000 (WebRTC).
        call_id: Unique identifier for the call.
    """
    logger.info("Starting Civora 311 bot")

    # Per-call state. Closed over by the tool functions below so each
    # call gets its own isolated ticket list.
    resolved_call_id = call_id or f"call_{random.randint(1000, 9999)}"
    call_state: dict = {"tickets": [], "caller_address": None, "call_id": resolved_call_id}

    async def send_dashboard_event(event_type: str, data: dict):
        dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:7861")
        url = f"{dashboard_url}/api/webhook/event"
        payload = {
            "event_type": event_type,
            "call_id": call_state["call_id"],
            "data": data
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=2.0) as r:
                    if r.status != 200:
                        logger.warning(f"Failed to send dashboard event: {r.status}")
        except Exception as e:
            logger.warning(f"Error sending dashboard event: {e}")

    # Fire call started event immediately
    await send_dashboard_event("call_started", {"caller_phone": from_number or "+1 (555) 311-0000"})

    # --- Tools the LLM can call ---------------------------------------------

    async def check_trash_schedule(
        params: FunctionCallParams,
        address: str,
    ) -> None:
        """Look up the trash and recycling pickup schedule for a given address.

        Use this when the caller asks about trash pickup, garbage collection,
        recycling schedule, or bin collection days.

        Args:
            address: The street address to look up. Use the caller's stated
                address, e.g. "123 Main Street" or "Oak Avenue, Midtown".
        """
        schedule = lookup_trash_schedule(address)
        logger.info(f"Trash schedule lookup: {address} -> {schedule}")
        await send_dashboard_event("tool_called", {
            "tool": "check_trash_schedule",
            "args": {"address": address},
            "result": schedule if isinstance(schedule, dict) else {"schedule": schedule},
            "status": "success"
        })
        await params.result_callback(schedule)

    async def create_pothole_ticket(
        params: FunctionCallParams,
        location: str,
        description: str,
    ) -> None:
        """File a pothole report. Only call this AFTER confirming the location
        with the caller by reading the address back to them.

        Args:
            location: The street address or intersection where the pothole is.
            description: Brief description of the pothole (size, depth, lane).
        """
        ticket_id = generate_ticket_id("pothole")
        ticket = {
            "ticket_id": ticket_id,
            "category": "Pothole",
            "location": location,
            "description": description,
            "status": "Open",
            "priority": "Normal",
        }
        call_state["tickets"].append(ticket)
        logger.info(f"Pothole ticket filed: {ticket}")
        await send_dashboard_event("tool_called", {
            "tool": "create_pothole_ticket",
            "args": {"location": location, "description": description},
            "result": {"ok": True, **ticket},
            "status": "success"
        })
        await send_dashboard_event("ticket_created", ticket)
        await params.result_callback({"ok": True, **ticket})

    async def report_broken_streetlight(
        params: FunctionCallParams,
        location: str,
    ) -> None:
        """File a broken streetlight report. Only call this AFTER confirming
        the location with the caller.

        Args:
            location: The street address or intersection of the broken streetlight.
        """
        ticket_id = generate_ticket_id("streetlight")
        ticket = {
            "ticket_id": ticket_id,
            "category": "Broken Streetlight",
            "location": location,
            "description": "Streetlight outage reported by citizen.",
            "status": "Open",
            "priority": "Normal",
        }
        call_state["tickets"].append(ticket)
        logger.info(f"Streetlight ticket filed: {ticket}")
        await send_dashboard_event("tool_called", {
            "tool": "report_broken_streetlight",
            "args": {"location": location},
            "result": {"ok": True, **ticket},
            "status": "success"
        })
        await send_dashboard_event("ticket_created", ticket)
        await params.result_callback({"ok": True, **ticket})

    async def report_water_leak(
        params: FunctionCallParams,
        location: str,
        severity: str = "moderate",
    ) -> None:
        """File a water leak report. Only call this AFTER confirming the
        location with the caller.

        Args:
            location: The street address or intersection of the water leak.
            severity: How bad is the leak. Values: "minor", "moderate", "severe".
                Default is "moderate".
        """
        is_severe = severity.lower() in {"severe", "high", "bad", "major", "emergency"}
        priority = "Urgent" if is_severe else "High"
        ticket_id = generate_ticket_id("water_leak")
        ticket = {
            "ticket_id": ticket_id,
            "category": "Water Leak",
            "location": location,
            "description": f"Water leak reported. Severity: {severity}.",
            "status": "Open",
            "priority": priority.lower(),
        }
        call_state["tickets"].append(ticket)
        logger.info(f"Water leak ticket filed: {ticket}")
        await send_dashboard_event("tool_called", {
            "tool": "report_water_leak",
            "args": {"location": location, "severity": severity},
            "result": {"ok": True, **ticket},
            "status": "success"
        })
        await send_dashboard_event("ticket_created", ticket)
        await params.result_callback({"ok": True, **ticket})

    async def report_graffiti(
        params: FunctionCallParams,
        location: str,
        description: str,
    ) -> None:
        """File a graffiti removal request. Only call this AFTER confirming
        the location with the caller.

        Args:
            location: The street address or location of the graffiti.
            description: What the graffiti looks like or says, and what surface
                it's on (wall, fence, sign, etc.).
        """
        ticket_id = generate_ticket_id("graffiti")
        ticket = {
            "ticket_id": ticket_id,
            "category": "Graffiti",
            "location": location,
            "description": description,
            "status": "Open",
            "priority": "Low",
        }
        call_state["tickets"].append(ticket)
        logger.info(f"Graffiti ticket filed: {ticket}")
        await send_dashboard_event("tool_called", {
            "tool": "report_graffiti",
            "args": {"location": location, "description": description},
            "result": {"ok": True, **ticket},
            "status": "success"
        })
        await send_dashboard_event("ticket_created", ticket)
        await params.result_callback({"ok": True, **ticket})

    async def report_abandoned_vehicle(
        params: FunctionCallParams,
        location: str,
        vehicle_description: str,
    ) -> None:
        """File an abandoned vehicle report. Only call this AFTER confirming
        the location with the caller.

        Args:
            location: The street address or location of the vehicle.
            vehicle_description: Description of the vehicle: color, make, model,
                license plate if visible.
        """
        ticket_id = generate_ticket_id("abandoned_vehicle")
        ticket = {
            "ticket_id": ticket_id,
            "category": "Abandoned Vehicle",
            "location": location,
            "description": f"Abandoned vehicle: {vehicle_description}.",
            "status": "Open",
            "priority": "Normal",
        }
        call_state["tickets"].append(ticket)
        logger.info(f"Abandoned vehicle ticket filed: {ticket}")
        await send_dashboard_event("tool_called", {
            "tool": "report_abandoned_vehicle",
            "args": {"location": location, "vehicle_description": vehicle_description},
            "result": {"ok": True, **ticket},
            "status": "success"
        })
        await send_dashboard_event("ticket_created", ticket)
        await params.result_callback({"ok": True, **ticket})

    async def get_city_policy(
        params: FunctionCallParams,
        topic: str,
    ) -> None:
        """Look up city policy or service information on a topic.

        Use this when the caller asks general questions about city services,
        rules, or procedures — things like "what are the quiet hours?",
        "when does the city plow snow?", or "how do I get a parking permit?".

        Args:
            topic: The topic to look up. Common values: "trash", "recycling",
                "pothole", "parking", "noise", "water", "streetlight", "graffiti",
                "abandoned vehicle", "snow", "tree", "permit".
        """
        # Try to match a known policy
        topic_lower = topic.lower()
        matched_key = None
        for key in CITY_POLICIES:
            if key in topic_lower or topic_lower in key:
                matched_key = key
                break

        if matched_key:
            result = {
                "topic": topic,
                "answer": CITY_POLICIES[matched_key],
                "found": True,
            }
        else:
            result = {
                "topic": topic,
                "answer": (
                    "I don't have that specific policy on file. I can connect you "
                    "with a human agent who may be able to help."
                ),
                "found": False,
            }
        logger.info(f"City policy lookup: {topic} -> found={result['found']}")
        await send_dashboard_event("tool_called", {
            "tool": "get_city_policy",
            "args": {"topic": topic},
            "result": result,
            "status": "success" if result["found"] else "error"
        })
        await params.result_callback(result)

    async def escalate_to_human(
        params: FunctionCallParams,
        reason: str,
    ) -> None:
        """Transfer the caller to a human agent. Use this when:
        - The caller explicitly asks to speak with a person
        - The caller is highly distressed or frustrated
        - The issue is outside the supported categories
        - You cannot resolve the request after a reasonable attempt

        Do NOT use this for emergencies — direct those to 911 instead.

        Args:
            reason: Brief explanation of why the call is being escalated.
        """
        ticket_id = generate_ticket_id("escalation")
        queue_position = random.randint(1, 4)
        ticket = {
            "ticket_id": ticket_id,
            "category": "Escalation",
            "location": "N/A",
            "description": f"Escalated to human agent. Reason: {reason}.",
            "status": "Escalated",
            "priority": "Urgent",
            "queue_position": queue_position,
        }
        call_state["tickets"].append(ticket)
        logger.info(f"Escalation: {ticket}")
        await send_dashboard_event("tool_called", {
            "tool": "escalate_to_human",
            "args": {"reason": reason},
            "result": {"ok": True, **ticket, "estimated_wait": f"about {queue_position * 2} minutes"},
            "status": "success"
        })
        await send_dashboard_event("ticket_created", ticket)
        await params.result_callback({
            "ok": True,
            **ticket,
            "estimated_wait": f"about {queue_position * 2} minutes",
        })

    async def end_call(params: FunctionCallParams) -> None:
        """End the call. Only call this AFTER you have said goodbye to the
        caller in the same turn. The pipeline will flush any queued speech
        and then hang up."""
        logger.info("end_call invoked — pushing EndTaskFrame upstream")
        await params.llm.push_frame(EndTaskFrame(), FrameDirection.UPSTREAM)
        # run_llm=False prevents the LLM from generating a follow-up response
        # after this function returns — the goodbye should already be in flight.
        await params.result_callback(
            {"ok": True}, properties=FunctionCallResultProperties(run_llm=False)
        )

    tool_functions = [
        check_trash_schedule,
        create_pothole_ticket,
        report_broken_streetlight,
        report_water_leak,
        report_graffiti,
        report_abandoned_vehicle,
        get_city_policy,
        escalate_to_human,
        end_call,
    ]
    tools = ToolsSchema(standard_tools=tool_functions)

    # --- System instruction (varies based on caller ID) ---------------------

    caller = KNOWN_CALLERS.get(from_number or "")
    if caller:
        caller_context = (
            f"This caller is a returning caller (caller ID matched). On file: "
            f"name {caller['name']}, address {caller['address']}. "
            'Greet them generically: "Hello, you\'ve reached City 311. How can '
            'I help you today?" Do not use their name in the greeting. '
            "If they report an issue, you can offer their address on file as a "
            f'shortcut: "I have {caller["address"]} on file — is that the right '
            'location?" Always let them correct it.'
        )
    else:
        caller_context = (
            "You're talking to a new caller. Introduce the service briefly and "
            "ask how you can help."
        )

    system_instruction = (
        "You are the City 311 Voice Assistant — an automated, government-service "
        "phone operator for a municipal non-emergency line. You help citizens "
        "report issues, file service requests, check city information, and reach "
        "a human when needed. Use the tools to look up schedules, file tickets, "
        "check policies, escalate, and end the call.\n\n"
        #
        "Talk like a real city service worker on the phone — not a chatbot:\n"
        "- Keep it to 1-2 short sentences per turn.\n"
        "- Ask ONE thing at a time. Don't ask for location, description, and "
        "severity in one breath — ask for the location, wait, then the next.\n"
        '- Skip filler openers like "Absolutely!", "I\'d be happy to help!", '
        '"That sounds terrible!" — go straight to the point.\n'
        "- Use plain language. No jargon, no bureaucratic phrases.\n"
        "- Use contractions. Fragments are fine.\n\n"
        #
        "Safety & emergencies (HIGHEST PRIORITY):\n"
        "- If a caller reports a life-threatening emergency (fire, active medical "
        "event, violent crime, gas leak, anything involving immediate danger to "
        "life), IMMEDIATELY tell them to hang up and call 911. Do NOT file a "
        "311 ticket for these. Say something like: \"That sounds like an emergency. "
        "Please hang up and call 911 right away.\"\n"
        "- Never give medical, legal, or safety instructions beyond \"call 911.\"\n\n"
        #
        "Address confirmation:\n"
        "- Always read the address back to the caller and ask them to confirm "
        "BEFORE filing any ticket.\n"
        "- For unclear addresses, ask the caller to spell the street name or "
        "provide a nearby landmark or cross street.\n\n"
        #
        "Tool-use rules:\n"
        "- Use the provided tools to take real action. Do not claim a ticket "
        "exists unless a tool returned a ticket ID.\n"
        "- After a tool returns a ticket ID, read the ID back to the caller "
        "slowly and clearly.\n\n"
        #
        "Escalation:\n"
        "- Escalate to a human when: the caller explicitly asks for a person, "
        "is highly distressed, the issue is outside supported categories, or "
        "you cannot resolve the request after a reasonable attempt.\n\n"
        #
        "No hallucination:\n"
        "- Never invent city policies, fees, timelines, or guarantees. If you "
        "don't know, say so and offer to file a request or connect a human.\n"
        "- Do not promise specific resolution times unless returned by a tool.\n\n"
        #
        "Privacy:\n"
        "- Do not ask for Social Security numbers, payment details, or sensitive "
        "identity documents. Remind callers not to share sensitive data.\n\n"
        #
        "Closing:\n"
        "- After filing a ticket, confirm the ticket ID and a brief next step, "
        "then ask if there's anything else.\n"
        "- When the caller has no more requests, or says goodbye: say a short "
        'closing line (e.g. "Thanks for calling 311. Have a good day!") AND call '
        "end_call in the same turn. Never call end_call without saying goodbye.\n\n"
        #
        "Responses are spoken aloud. No bullet points, no emojis. Read ticket "
        'IDs clearly (e.g. "P-O-T dash two-four-zero-five-three-zero dash zero-'
        'zero-one").\n\n'
        f"Today is {date.today().strftime('%A, %B %d, %Y')}.\n\n"
        f"Caller context: {caller_context}"
    )

    # Speech-to-Text service
    #
    # Gradium STT for cloud deployment (NVIDIA ASR is on private hackathon
    # network, unreachable from Pipecat Cloud).
    stt = GradiumSTTService(
        api_key=os.environ["GRADIUM_API_KEY"],
        settings=GradiumSTTService.Settings(
            language=Language.EN,
        ),
    )

    # LLM service — Nemotron-3-Super-120B served by vLLM (OpenAI-compatible chat
    # completions at /v1). vLLM exposes the Chat Completions API, not the Responses
    # API, so we use OpenAILLMService (not OpenAIResponsesLLMService). The live
    # endpoint serves the model as "nemotron-3-super" (per its /v1/models).
    #
    # Reasoning ("thinking") toggle — Nemotron is controlled per-request via
    # chat_template_kwargs.enable_thinking, forwarded through the OpenAI client's
    # extra_body (the request-body convention confirmed against this endpoint in
    # ../aiewf-eval traces). Default OFF for low-latency voice. To ENABLE, set
    # NEMOTRON_ENABLE_THINKING=true; to DISABLE, leave unset/false.
    #
    # CAUTION for voice: reasoning is only kept out of the spoken `content` if the
    # vLLM server runs a reasoning parser (e.g. --reasoning-parser nemotron_v3, which
    # routes it to a separate `reasoning_content` field). This live endpoint did NOT
    # surface reasoning_content in testing, so if thinking is enabled and the server
    # lacks a parser, chain-of-thought would appear inline in `content` and get
    # spoken. Keep thinking OFF for voice unless the parser is confirmed active.
    # VLLMOpenAILLMService is a thin OpenAILLMService subclass that reports TTFB to
    # the first NON-THINKING token (so the metric reflects time-to-first-spoken-word
    # when reasoning is enabled, not time-to-first-reasoning-token). No-op when
    # thinking is off. See server/nemotron_llm.py.
    enable_thinking = os.getenv("NEMOTRON_ENABLE_THINKING", "false").lower() == "true"
    llm = VLLMOpenAILLMService(
        api_key=os.getenv("NEMOTRON_LLM_API_KEY", "EMPTY"),  # vLLM ignores unless --api-key set
        base_url=os.getenv("NEMOTRON_LLM_URL", "http://192.168.7.228:8000/v1"),
        settings=VLLMOpenAILLMService.Settings(
            model=os.getenv("NEMOTRON_LLM_MODEL", "nvidia/nemotron-3-super"),
            system_instruction=system_instruction,
            extra={"extra_body": {"chat_template_kwargs": {"enable_thinking": enable_thinking}}},
        ),
    )

    # Text-to-Speech service
    voice_id = os.getenv("GRADIUM_VOICE_ID", "Eu9iL_CYe8N-Gkx_")
    if not voice_id or not voice_id.strip():
        voice_id = "Eu9iL_CYe8N-Gkx_"

    tts = GradiumTTSService(
        api_key=os.environ["GRADIUM_API_KEY"],
        settings=GradiumTTSService.Settings(
            voice=voice_id,
        ),
    )

    # ToolsSchema describes the tools to the LLM; register_direct_function
    # wires the actual handlers the LLM will invoke. Both are required.
    for fn in tool_functions:
        llm.register_direct_function(fn)

    context = LLMContext(tools=tools)
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(),
            user_turn_strategies=FilterIncompleteUserTurnStrategies(),
        ),
    )

    notifier = DashboardNotifier(send_dashboard_event)

    # Pipeline - assembled from reusable components
    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            notifier,
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
            audio_in_sample_rate=audio_in_sample_rate,
            audio_out_sample_rate=audio_out_sample_rate,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Client connected")
        # Kick off the conversation
        context.add_message(
            {
                "role": "user",
                "content": "A citizen just called the 311 line. Greet them: 'Hello, you've reached City 311. How can I help you today?'",
            }
        )
        await worker.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        await notifier.flush_assistant_text()
        await send_dashboard_event("call_ended", {})
        await worker.cancel()

    runner = WorkerRunner(handle_sigint=False)

    await runner.add_workers(worker)
    await runner.run()


async def bot(runner_args: RunnerArguments):
    """Main bot entry point."""

    from_number: str | None = None
    transport_overrides: dict = {}

    # Krisp is available when deployed to Pipecat Cloud
    if os.environ.get("ENV") != "local":
        from pipecat.audio.filters.krisp_viva_filter import KrispVivaFilter

        krisp_filter = KrispVivaFilter()
    else:
        krisp_filter = None

    call_id: str | None = None
    match runner_args:
        case SmallWebRTCRunnerArguments():
            webrtc_connection: SmallWebRTCConnection = runner_args.webrtc_connection
            call_id = f"call_webrtc_{random.randint(1000, 9999)}"

            transport = SmallWebRTCTransport(
                webrtc_connection=webrtc_connection,
                params=TransportParams(
                    audio_in_enabled=True,
                    audio_in_filter=krisp_filter,
                    audio_out_enabled=True,
                ),
            )
        case WebSocketRunnerArguments():
            # Twilio media streams are 8 kHz μ-law in both directions.
            # This overrides the default sample rates: 16 kHz in / 24 kHz out.
            transport_overrides["audio_in_sample_rate"] = 8000
            transport_overrides["audio_out_sample_rate"] = 8000

            # Parse Twilio websocket and fetch call information
            _, call_data = await parse_telephony_websocket(runner_args.websocket)
            call_id = call_data["call_id"]

            # Fetch call information from Twilio REST API so we can personalize
            # the bot for known callers (see KNOWN_CALLERS).
            call_info = await get_call_info(call_data["call_id"])
            if call_info:
                from_number = call_info.get("from_number")
                logger.info(f"Call from: {from_number} to: {call_info.get('to_number')}")

            serializer = TwilioFrameSerializer(
                stream_sid=call_data["stream_id"],
                call_sid=call_data["call_id"],
                account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
                auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
            )

            transport = FastAPIWebsocketTransport(
                websocket=runner_args.websocket,
                params=FastAPIWebsocketParams(
                    audio_in_enabled=True,
                    audio_in_filter=krisp_filter,
                    audio_out_enabled=True,
                    add_wav_header=False,
                    serializer=serializer,
                ),
            )
        case _:
            logger.error(f"Unsupported runner arguments type: {type(runner_args)}")
            return

    await run_bot(transport, from_number=from_number, call_id=call_id, **transport_overrides)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
