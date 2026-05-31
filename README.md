# City311 — Municipal Voice Assistant

A 24/7 voice agent that answers your city's 311 line, files real service tickets, and routes emergencies to 911 — no hold music required.

> [!IMPORTANT]
> 📞 **Call the live demo: (956) 476-4454**
> Report a pothole, ask about trash pickup, or try to break it. The bot is the deployed `civora-311` agent on Pipecat Cloud, answering a real Twilio number.

## 1. What is this?

Municipal 311 lines are overloaded. Citizens calling to report a pothole, a broken streetlight, or a missed trash pickup routinely wait 10+ minutes on hold — and many just give up. Cities pay overtime for human operators to handle calls that are 90% structured intake: name, address, issue type, priority.

City311 is a voice agent that picks up on the first ring, runs a natural conversation, and files a real ticket with a tracking ID before the citizen hangs up. It exposes **nine** city-service tools (potholes, streetlights, water leaks, graffiti, abandoned vehicles, trash schedule, city policy lookup, human escalation, `end_call`), confirms addresses to prevent hallucinated tickets, and hard-redirects to 911 the moment it detects a life-safety emergency.

Three ways to try it: **call the number above**, open the web dashboard to watch live transcripts and ticket creation stream in over SSE, or run the local bot against a browser WebRTC client. The cloud bot runs on Pipecat Cloud with NVIDIA Nemotron (LLM), Gradium (STT/TTS), Krisp noise filtering, and a custom `DashboardNotifier` that taps the pipeline for real-time observability.

## 2. Video demo (< 60 s)

▶ Watch the 60-second demo: **[[insert hosted video link here before submission](https://drive.google.com/drive/folders/17VxuDJi4ekR6lik4DLziGYzSZabeLTHF?usp=sharing)]**

## 3. The problem

- **Hold times are brutal.** Non-emergency 311 lines routinely queue callers for 10+ minutes while a small pool of human agents triages requests one at a time.
- **After hours, the line goes dark.** Most municipal 311 desks close evenings, weekends, and holidays — exactly when potholes, outages, and leaks get noticed.
- **Most of the work is repetitive triage.** "What's the address? What kind of issue? When did it start?" — same intake script, thousands of times a day, burning capacity that should go to hard cases.
- **Intake quality is inconsistent.** Tickets land with missing addresses, vague categories, and no priority, forcing field crews to chase clarifications before dispatch.
- **The long tail never gets reported.** A burned-out streetlight isn't worth a 12-minute phone call, so citizens shrug and the city never hears about it.

## 4. The solution

- **Always-on voice line on a real phone number.** Call **(956) 476-4454** any time — Twilio Media Streams into Pipecat Cloud, picked up by `civora-311`.
- **Structured tool-calling for every category.** Nine first-class tools cover potholes, streetlights, water leaks, graffiti, abandoned vehicles, trash-schedule lookup, city-policy Q&A, human escalation, and call termination — every request becomes a typed ticket, not a freeform note.
- **Address confirmation and ticket IDs read back.** The agent confirms the street address before filing, then reads back a category-prefixed ticket ID (e.g. `POT-…`, `LGT-…`, `WTR-…`) so the caller hangs up with a reference number.
- **911 emergency redirect baked into the prompt.** Life-safety language triggers an immediate redirect to 911 instead of a 311 ticket — guardrails live in the system prompt, not bolted on.
- **Real-time operator dashboard.** Live transcripts, tickets, and tool calls stream into a React dashboard via FastAPI + SSE (`/api/events/stream`) the instant they happen on the bot — no polling, no seed data.

## 5. Why this wins

- **NVIDIA Nemotron-3-Super (vLLM, OpenAI-compatible)** drives both reasoning and tool selection through a thin `VLLMOpenAILLMService` wrapper with per-request `enable_thinking` — one open-weights model handles "is this a pothole or a sinkhole?", "is this a 911?", and the JSON tool call, with no router glue.
- **Pipecat orchestrates the whole pipeline** — `transport.input → STT → user-aggregator → LLM → DashboardNotifier → TTS → transport.output → assistant-aggregator` — with Silero VAD, Krisp Viva noise filtering on the Twilio leg, and a custom `FrameProcessor` that taps the stream for the dashboard without blocking audio.
- **Judges can call it right now.** Deployed to Pipecat Cloud as `civora-311` (`agent_profile = agent-1x`, `min_agents = 1`), wired to a real Twilio DID via a TwiML Bin pointing at `wss://api.pipecat.daily.co/ws/twilio` — no demo mode.
- **Cekura-evaluated across 5 scenario types.** Agent `18056` / project `5918` runs pothole intake, trash-schedule lookup, streetlight outage, 911 emergency redirect, and a frustrated repeat-caller human escalation against an 11-dimension scoring rubric (result set `591340`), with weak dimensions feeding a prompt-patch / re-run loop.
- **Honest dashboard, no theatre.** Seed data is explicitly disabled (`dashboard/backend/app/state.py:35-36`, `MOCK_*` blocks in `api.ts` neutralized, `Dashboard.tsx` transcript state starts empty); every ticket, transcript line, and tool call you see came from a real call.

## 6. Architecture

```
                         ┌──────────────────┐
   ☎  Caller  ─────────► │  Twilio Voice    │  (956) 476-4454
                         │  + Media Streams │  8 kHz μ-law, bidirectional
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │   TwiML Bin      │  <Stream url="wss://api.pipecat.daily.co/ws/twilio">
                         │  (Twilio-hosted) │  _pipecatCloudServiceHost = civora-311.<org>
                         └────────┬─────────┘
                                  │  WebSocket (audio in/out)
                                  ▼
   ┌───────────────────────────────────────────────────────────────────┐
   │                  Pipecat Cloud  ·  agent: civora-311              │
   │                  (krisp_viva "tel" filter on ingress, cloud only) │
   │                                                                   │
   │   transport.input → Gradium STT ─► user_aggregator (Silero VAD)   │
   │                                         │                         │
   │                                         ▼                         │
   │                              ┌────────────────────┐               │
   │                              │  Nemotron-3-Super  │◄─── 9 tools ──┤
   │                              │  (vLLM on AWS)     │   pothole,    │
   │                              │  enable_thinking   │   streetlight,│
   │                              └─────────┬──────────┘   trash, etc. │
   │                                        │  (tool result)           │
   │                                        ▼                          │
   │                                DashboardNotifier ──── webhook ───►│
   │                                        │             (aiohttp)    │
   │                                        ▼                          │
   │                                  Gradium TTS                      │
   │                                        │                          │
   │                                        ▼                          │
   │                                 transport.output ──► caller       │
   └───────────────────────────────────────┬───────────────────────────┘
                                           │  POST /api/webhook/event
                                           ▼  (via ngrok tunnel)
                                  ┌──────────────────┐
                                  │  FastAPI         │   in-memory Store
                                  │  dashboard       │   (calls, tickets,
                                  │  backend :7861   │    tool_calls, evals)
                                  └────────┬─────────┘
                                           │  GET /api/events/stream
                                           ▼  (Server-Sent Events)
                                  ┌──────────────────┐        ┌─────────┐
                                  │  React + Vite    │◄──────►│ Cekura  │
                                  │  dashboard UI    │  evals │ agent   │
                                  │  (Tailwind)      │        │ 18056   │
                                  └──────────────────┘        └─────────┘
```

Audio rides Twilio → Pipecat Cloud, where Gradium STT, Nemotron, and Gradium TTS form the speech loop and 9 registered city-service tools run inline against the mock 311 backend. Every transcript, tool call, and ticket is mirrored through a webhook over ngrok to the FastAPI backend, which fans events out to the React dashboard via SSE and triggers Cekura scenario runs for the self-improvement loop.

## 7. Tech stack

| Layer | Service | Sponsor / source |
| --- | --- | --- |
| Orchestration | Pipecat pipeline + Pipecat Cloud (`agent_profile = agent-1x`, `min_agents = 1`) | Daily |
| STT | Gradium Speech-to-Text (`GradiumSTTService`, Language.EN) | Gradium (credits provided) |
| LLM | NVIDIA Nemotron-3-Super served via vLLM (OpenAI-compatible) on AWS ALB, per-request `enable_thinking` | NVIDIA + AWS |
| TTS | Gradium Text-to-Speech (`GradiumTTSService`, configurable `voice_id`) | Gradium (credits provided) |
| Telephony | Twilio Voice + Media Streams (8 kHz μ-law) wired via TwiML Bin → Pipecat Cloud | Twilio |
| Evaluation | Cekura — 5 generated scenarios, 11-dimension scoring, result set 591340 (agent 18056 / project 5918) | Cekura |
| Frontend | React 18 + Vite 5 + TypeScript + Tailwind (+ Framer Motion, Recharts, lucide-react) | OSS, re-skinned to City311 |
| Backend | FastAPI + uvicorn + Pydantic v2 + SSE (`/api/events/stream`) + aiohttp webhook client | OSS |
| Deploy | Pipecat Cloud via `pcc-deploy.toml` + `Dockerfile`, secret set `civora-311-secrets` | Daily + Docker |
| Dev | `uv` for Python deps, `ngrok` tunnel for dashboard webhook ingress | Astral + ngrok |

## 8. How we used Cekura, Nemotron, and Pipecat

City311 is built on the **Pipecat + NVIDIA Nemotron + Cekura** stack end-to-end: Pipecat orchestrates the realtime voice loop, Nemotron does the reasoning and tool selection, and Cekura grades every release against a fixed scenario suite so we iterate on the prompt instead of guessing.

### Pipecat (orchestration)

- **Realtime voice pipeline.** Each call runs through a single Pipecat `Pipeline` wired as `transport.input → STT → user_aggregator → LLM → DashboardNotifier → TTS → transport.output → assistant_aggregator` (`server/bot.py:653-664`). `GradiumSTTService` for STT, `VLLMOpenAILLMService` for the LLM, `GradiumTTSService` for TTS, with `SileroVADAnalyzer` + `FilterIncompleteUserTurnStrategies` in the user aggregator so the model only sees complete turns.
- **Tool calling via `OpenAILLMContext` + `ToolsSchema`.** Nine direct functions registered through `llm.register_direct_function` (`server/bot.py:485-496, 638-639`). Nemotron picks the right tool per turn; tool outputs (ticket IDs, schedules) flow back into the same context so the assistant can read them aloud in the next response.
- **Custom `DashboardNotifier` FrameProcessor.** Tapped between LLM and TTS — watches `TranscriptionFrame`, `TextFrame`, `UserStartedSpeakingFrame` and POSTs `transcript_added` / `tool_called` / `call_started` events to the dashboard webhook with a 2.0 s timeout (`server/bot.py:112-192`). Backend fans these out to the React UI via SSE on `/api/events/stream`.
- **Twilio Media Streams transport + Pipecat Cloud deploy.** Inbound PSTN calls hit a TwiML Bin pointing at `wss://api.pipecat.daily.co/ws/twilio`, served by `FastAPIWebsocketTransport`. Sample rates are overridden to **8 kHz in/out on the Twilio path** (defaults are 16 kHz in / 24 kHz out for the WebRTC path) — `server/bot.py:730-733`. Agent deploys to Pipecat Cloud as `civora-311` (`server/pcc-deploy.toml`); Krisp `tel` audio filter is enabled in cloud (not local).
- **Framework footgun we hit and fixed.** First cut of `DashboardNotifier.process_frame` was missing `await self.push_frame(frame, direction)` — the processor silently swallowed every frame between LLM and TTS, callers heard dead air. Base `FrameProcessor.process_frame` does not auto-forward, no runtime warning. Fix at `server/bot.py:142` with an inline `CRITICAL` comment; documented in Troubleshooting.

### NVIDIA Nemotron (LLM + open weights)

- **Model: `nvidia/nemotron-3-super` via vLLM.** Reached through a vLLM OpenAI-compatible endpoint on AWS (`NEMOTRON_LLM_URL=http://nemotron-fleet-alb-...us-west-2.elb.amazonaws.com/v1`) via a thin `VLLMOpenAILLMService` subclass of `OpenAILLMService` (`server/nemotron_llm.py`). Open-weights Nemotron is the only LLM in the cloud path.
- **One model for both conversation and structured tool selection.** Nemotron handles natural conversational replies and structured tool-call decisions across all nine tools — same model decides *whether* a turn is a ticket vs policy lookup vs 911 redirect, and then *executes* it via standard OpenAI function-calling.
- **Thinking mode on for safety-critical routing.** `enable_thinking=true` forwarded via `extra_body.chat_template_kwargs` (`server/bot.py:613-621`). Gives Nemotron room to reason through emergency-vs-ticket-vs-escalation routing before committing to a tool.
- **Reasoning tokens stripped before TTS.** Our wrapper defers `stop_ttfb_metrics` until the first non-thinking delta arrives — gates on `content` or `tool_calls` in the delta rather than firing on the first chunk (`server/nemotron_llm.py:55-80`). Reasoning stays inside the LLM service, never reaches TTS.

### Cekura (evaluation + improvement)

- **What we wanted.** A repeatable, judgeable answer to *"is this bot actually good at being a 311 operator?"* — not vibes-based prompt tweaking. Five scenarios cover the failure surface: (1) clean pothole report, (2) trash-schedule lookup (no ticket), (3) streetlight outage + safety concern, (4) 911 emergency redirect (must refuse to file a ticket), (5) frustrated repeat-caller (must escalate). Each scenario scored on Cekura's 11-dimension rubric.
- **How we used it.** Installed the `cekura-skills` Claude Code plugin, used it to create **agent 18056 in project 5918** with the Pipecat provider pointing at the deployed `civora-311` cloud agent, generated all five scenarios in parallel, launched **result set 591340** against the live cloud bot. Cekura drives synthetic callers into the same Twilio entry point real users hit — scoring reflects the actual production pipeline.
- **Improvement loop — what we shipped.** Honest about what's verified: result set 591340 is the live record (judges can verify in the Cekura dashboard), and we used its per-dimension findings to ship concrete prompt patches. Fixes that came out of the loop and are in `server/bot.py`: (a) **address confirmation read-back** before filing any ticket, after address-capture flagged silent mis-hears; (b) **hardened 911 guardrail** — the model now refuses to file a ticket *and* states the redirect in the same turn; (c) **shorter turn length** — capped response length in the prompt after conversation-quality dimensions flagged monologuing. Specific numeric *"X% → Y%"* deltas are intentionally **not** claimed because we did not finalize a re-run baseline within the hackathon window — the loop and the patches are real, the final scoreboard lives in Cekura result set 591340.

## 9. What we built during the hackathon

Started from the YC × Pipecat hackathon starter ("Field & Flower" voice agent template, plus a sponsor commit adding Nemotron endpoints). Everything below was built on top of that base in a single ~12-hour push.

### New during the hackathon

- **Entire City311 voice agent domain** — new system prompt with safety guardrails (911 redirect, address read-back, anti-hallucination on city policies) and a tool-call schema covering every supported request type.
- **Nine tools** registered via `ToolsSchema` + `llm.register_direct_function`: `create_pothole_ticket`, `check_trash_schedule`, `report_broken_streetlight`, `report_water_leak`, `report_graffiti`, `report_abandoned_vehicle`, `get_city_policy`, `escalate_to_human`, `end_call`.
- **Mock 311 backend** (`server/mock_backend.py`) — trash schedules for 10 neighborhoods, 12 city-policy answers, 2-entry known-caller registry, per-call in-memory ticket storage, typed ticket-ID prefixes (`POT/LGT/WTR/GRF/VEH/NOI/TRS/TRE/GEN/ESC`).
- **Custom `DashboardNotifier` FrameProcessor** with the silent-audio bug fix (see Pipecat section above).
- **Real-time FastAPI dashboard backend** — `POST /api/webhook/event` ingest (5 event types), `GET /api/events/stream` SSE fan-out with 15 s keep-alive and `X-Accel-Buffering: no`, plus REST endpoints for calls / tickets / tool-calls / evals.
- **React + Vite + Tailwind dashboard frontend** — Hero, Operator Dashboard, Active Call panel, Live Transcript, Tickets table, Tool Call feed, Evaluation Loop view, System Architecture diagram. `lib/api.ts` types fetch + `EventSource` subscription.
- **Branding rename Civora → City311** across the frontend (`App.tsx`, `Hero.tsx`, `Navbar.tsx`, `index.html`).
- **Stripped all seeded/mock data** — `state.py` seed disabled, `api.ts` `MOCK_*` blocks neutralized, `Dashboard.tsx` transcript state starts empty.
- **Twilio phone-line provisioning** — TwiML Bin wired to **(956) 476-4454**. Helper scripts in `server/`: `setup_phone_line.py`, `setup_pipecat_cloud_phone.py`, `get_twiml_bin.py`, `check_twilio_number.py`.
- **Pipecat Cloud deployment** as agent `civora-311` (see `pcc-deploy.toml`). `Dockerfile` updated to copy `nemotron_llm.py` and `nvidia_stt.py`.
- **NVIDIA Nemotron LLM wrapper** (`server/nemotron_llm.py`) — defers `stop_ttfb_metrics` until first non-thinking delta, forwards `enable_thinking`, defensive stream close.
- **NVIDIA Parakeet WebSocket STT client** (`server/nvidia_stt.py`) for the local browser path; cloud bot falls back to **Gradium STT** because Parakeet expects 16 kHz PCM while Twilio sends 8 kHz μ-law (see Feedback).
- **ngrok bridge** so the cloud bot's webhooks reach the local dashboard (`DASHBOARD_URL` in `.env.cloud`), with a 2.0 s POST timeout so a slow dashboard never blocks audio.
- **Cekura self-improvement loop** — agent 18056, project 5918, 5 scenarios, result set 591340. `app/cekura_client.py` drives runs from the dashboard.
- **Direct-service verifier scripts** — `test_asr_direct.py`, `test_nemotron_direct.py`, `test_gradium_direct.py`, `simulate_live_bot_call.py` for isolating which dependency is failing.

### Borrowed (not built here)

- **YC Pipecat hackathon starter repo** ("Field & Flower" template) — base `Dockerfile`, runner wiring, transport switching, `bot-gpt.py` as a GPT-4.1 reference. Git log shows two pre-hackathon commits — everything after is hackathon work.
- **Pipecat framework + Pipecat Cloud infra** (Daily) — `FrameProcessor` base, `Pipeline` / `PipelineRunner`, Twilio + WebRTC transports, `SileroVADAnalyzer`, `KrispVivaFilter`, OpenAI-compatible LLM service interface.
- **NVIDIA Nemotron + Parakeet inference endpoints** — hosted by NVIDIA/AWS for the hackathon. We wrote the clients; we did not host the models.
- **Gradium STT/TTS** — production speech path for the cloud bot.
- **Dashboard UI scaffolding** — Vite + React + Tailwind + Framer Motion + Recharts shell, shadcn-style primitives, lucide-react icons from a prior dashboard scaffold. Re-skinned and wired to the real webhook / SSE feed.

## 10. Feedback on the tools

### NVIDIA Nemotron-3-Super

**What worked well:**
- Tool selection across nine tools was reliable — over a full demo session we did not catch a wrong-tool invocation, and it correctly distinguished e.g. *"the light at 5th and Main is out"* (streetlight) from *"there's a pit in the road"* (pothole).
- Thinking mode produced visibly better safety routing — 911-class inputs were redirected to the emergency script without ever opening a ticket.
- The model followed voice-friendly prompting (no markdown, contractions, short sentences) consistently — no post-processing on TTS-bound text.
- The vLLM OpenAI-compatible endpoint dropped straight into Pipecat's `OpenAILLMService` — our `VLLMOpenAILLMService` is a ~40-line subclass; no bespoke transport, no auth dance.

**What could be better:**
- LLM TTFB was perceptible in cloud (multi-hundred-ms to low-seconds range) — noticeable pause before the greeting and after each user turn.
- Reasoning/thinking deltas came through the OpenAI-compat stream as regular content chunks — would have leaked into `TextFrame`s headed for TTS if we hadn't gated on `content` / `tool_calls` ourselves. This gotcha is not surfaced in the OpenAI-compat path and should either be filtered server-side or be a documented flag.
- Even with thinking gated, Nemotron occasionally restated its reasoning inside the user-facing answer until we tightened the system prompt. A first-class `reasoning` channel separate from `content` (like some other providers expose) would remove the need for prompt hacks.
- Parakeet streaming ASR expects 16 kHz PCM, but Twilio Media Streams deliver 8 kHz μ-law in both directions. There is no built-in resampler or 8 kHz μ-law mode that we could find — symptom was 8–17 s STT TTFB and repeated "hard reset" loops, which forced the deployed agent to fall back to Gradium STT for the Twilio path. A documented ingress resampler, or first-class μ-law support, would unblock an end-to-end NVIDIA stack.

### Cekura

**What worked well:**
- `/plugin install cekura@cekura-skills` was the smoothest tool install of the day — single command, no API key dance.
- `/cekura-report` drove agent creation, scenario generation, and run launch from a single command — went from "no eval harness" to agent 18056 / project 5918 with five scenarios queued and result set 591340 running, without leaving the editor.
- The 11-dimension per-scenario scoring gave specific, actionable feedback (address capture, escalation precision, hallucination rate, etc.) — could point at one weak dimension and write a targeted prompt patch.
- Native Pipecat provider — Cekura called the deployed cloud agent directly over the same Twilio path real callers use, with zero glue code.

**Self-improvement loop feedback / bugs:**
- Real-time progress visibility while a result set is executing is limited — we ended up re-asking "is it done yet?" A `/cekura-progress <result_set_id>` (scenarios complete / in-flight / queued) would remove the polling.
- The loop is still human-in-the-loop: read metrics → edit system prompt → redeploy → re-run. A "suggest prompt patches" mode that proposes a concrete system-prompt diff from the worst-scoring dimensions would close the loop.
- Scenario discovery across folders/agents from the CLI is harder than it should be — we lost a scenario once by re-generating into a new folder instead of finding the old one.
- When a scenario aborts for infra reasons (cold-start timeout, Twilio drop) it lands in the same result table as genuinely low-quality runs — muddies the signal on small result sets. A "infra failure / not scored" status column would sharpen the picture.

### Pipecat / Pipecat Cloud

**What worked well:**
- One framework covers WebRTC dev *and* Twilio production — `RunnerArguments` pattern-matching switches transport with zero pipeline change.
- Pipecat Cloud's `pc cloud deploy` + secret-set workflow is fast — push a new image and a redeploy in ~75 s; secrets are managed separately from the image.
- Built-in Krisp Viva noise filter for the Twilio leg is a single config flag — meaningful audio quality lift in cloud calls.

**What could be better:**
- **Silent-`push_frame` footgun.** A custom `FrameProcessor` that overrides `process_frame` but forgets `await self.push_frame(frame, direction)` silently swallows every frame downstream — no warning, no log, just dead air. We lost ~30 min root-causing this with Pipecat Cloud logs. A runtime check ("processor `X` consumed `Y` frames without forwarding any in the last `N` seconds") would prevent it entirely.
- The cloud logs view is per-session but lacks an easy "tail latest session" — we kept fetching last 200 lines and grepping. `pc cloud agent logs --follow` is missing.
- Sample-rate plumbing between transport and STT (the 8 kHz / 16 kHz Twilio ↔ Parakeet mismatch) needs more obvious documentation — the rates flow through `audio_in_sample_rate` overrides and silently break STT services with fixed input rates.

## 11. Run it yourself

Three terminals plus one deploy command. All copy-pasteable, all matches what's running.

**Terminal 1 — Dashboard backend (FastAPI on :7861)**

```bash
cd dashboard/backend
.venv/bin/uvicorn server:app --port 7861 --reload
```

**Terminal 2 — Dashboard frontend (Vite on :5173)**

```bash
cd dashboard/frontend
npm run dev
```

Vite proxies `/api/*` to `:7861`, so SSE and REST Just Work in dev.

**Terminal 3 — Public tunnel for the cloud bot's webhooks**

```bash
ngrok http 7861
```

Copy the `https://<your-ngrok>.ngrok-free.dev` URL and set it as `DASHBOARD_URL` in `server/.env.cloud`.

**Deploy the voice bot to Pipecat Cloud**

```bash
cd server
pc cloud secrets set civora-311-secrets --file .env.cloud
pc cloud deploy
```

Cloud agent is `civora-311` on Pipecat Cloud (your org). The TwiML Bin on the phone number points at `wss://api.pipecat.daily.co/ws/twilio` with `_pipecatCloudServiceHost = civora-311.<your-org>`. Once deployed, call **(956) 476-4454**.

> [!TIP]
> The dashboard starts **empty**. Every ticket, transcript line, and tool call is from a real call — no seed data, no mocks.

## 12. Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Phone connects, two-way silence | A custom `FrameProcessor` (e.g. `DashboardNotifier`) is swallowing frames because `process_frame` doesn't forward them | Add `await self.push_frame(frame, direction)` at the **end** of every `process_frame` override — Pipecat does not auto-forward |
| Cloud bot live but dashboard never updates | `DASHBOARD_URL` is `http://localhost:7861` — Pipecat Cloud can't reach your laptop | Run `ngrok http 7861`, put the HTTPS URL in `server/.env.cloud` as `DASHBOARD_URL`, redeploy |
| STT TTFB 8–17 s + "hard reset" loops over Twilio | NVIDIA Parakeet expects 16 kHz PCM, Twilio delivers 8 kHz μ-law | Resample on ingress, or swap STT to `GradiumSTTService` (what `civora-311` does) |
| `curl` against the TwiML Bin returns `Not Authorized` | Bin handler only accepts signed Twilio requests | Inspect the bin via the Twilio Console UI or the REST API (`/2010-04-01/Accounts/{sid}/IncomingPhoneNumbers`) |

## 13. Security notes (hackathon scope)

This code is sized for a hackathon demo and is **not production-hardened**. The following gaps are known and accepted within the demo window:

- **`/api/webhook/event` has no authentication.** The dashboard backend trusts any POST that lands on it. The webhook is reached via an ngrok tunnel exposing `localhost:7861`. Mitigation in production: shared HMAC secret in the `X-Webhook-Secret` header, compared in constant time. The same secret would live in `server/.env.cloud` (passed via `pc cloud secrets`) and the dashboard backend's `.env`.
- **CORS is wide open (`allow_origins=["*"]`).** Combined with the unauthenticated webhook, any page open in a browser can POST to the dashboard. Tighten to the dev origin (`http://localhost:5173`) and the deployed frontend origin before any non-demo use.
- **`/twilio/voice` does not verify `X-Twilio-Signature`.** Anyone who knows the public webhook URL can fetch the TwiML and learn the Pipecat Cloud agent endpoint. Production fix: validate the signature with `twilio.request_validator.RequestValidator(auth_token)`.
- **`/api/demo/*` and `/api/evals/run` are unauthenticated.** During the demo this is fine (the surface is small and time-bounded), but in production these should be behind an operator session or removed entirely. Of note, `/api/evals/run` triggers Cekura runs and consumes credits.

**Post-demo checklist:** rotate the ngrok tunnel hostname, rotate the Twilio Auth Token, and rotate the Gradium API key. The demo phone number is fine to keep.

## Acknowledgements

Built during the **YC Voice Agents Hackathon**, hosted by **Cekura** and **Daily**, in partnership with **NVIDIA**, **AWS**, and **Twilio**.

Thanks to **Daily** for the Pipecat starter template and the Pipecat Cloud credits that hosted `civora-311`; to **NVIDIA** and **AWS** for the Nemotron + Parakeet inference fleet behind the AWS-hosted vLLM endpoint; to **Gradium** for the STT and TTS credits that carry the deployed bot's voice path; to **Cekura** for the evaluation credits and the 11-dimension scoring loop (agent 18056, project 5918); and to **Twilio** for the trial credits plus the live phone number callers actually dial.
