# Civora® — Municipal 311 City Assistant

**An AI-powered 311 voice assistant that answers city service calls, files tickets, escalates emergencies, and continuously improves itself through automated voice testing.**

> Built for the Y Combinator Voice Agents Hackathon · Twilio · Daily/Pipecat · AWS Nova Sonic · NVIDIA NIM · Cekura

---

## The Problem

Citizens call 311 to report potholes, missed garbage pickup, broken streetlights, water leaks, abandoned vehicles, graffiti, noise, and parking issues — and to ask routine questions about city services. City call centers face long hold times, overwhelmed operators, and inconsistent service quality, especially during weather events and peak hours.

## The Solution

Civora is an AI phone operator citizens can call on a real Twilio number. It listens, understands intent, asks the right follow-up questions, confirms addresses, files structured city service tickets, escalates genuine emergencies to 911, and reads back confirmation numbers — in multiple languages. Every call streams to a live operator dashboard, and an automated testing loop (Cekura) measures quality and drives prompt self-improvement.

## Demo Flow

1. A judge calls the Twilio number (or clicks **Start Demo Call** in the dashboard).
2. They report an issue, e.g. *"There's a huge pothole on Market Street near 5th."*
3. The transcript appears live; the agent confirms the location and files a ticket.
4. The new ticket appears **instantly** in the City Ticket Database, with the tool call shown in the Tool Call Feed.
5. The judge clicks **Run Stress Test** — Cekura scenarios run and evaluation scores populate the chart.
6. Weak dimensions trigger the **self-improvement loop**: a new prompt version is created with targeted guidance, visible on the prompt-version timeline.

---

## Architecture

```
Citizen Phone
     │  (PSTN)
     ▼
  Twilio  ── Programmable Voice + Media Streams (WebSocket audio)
     │
     ▼
 FastAPI WebSocket  (/twilio/media)
     │
     ▼
  Pipecat  ── realtime conversational orchestration
     │
     ├──▶ AWS Bedrock Nova Sonic   (speech-to-speech model)
     ├──▶ NVIDIA NIM               (high-accuracy address ASR / verification)
     └──▶ 311 Tools                (file tickets, lookups, escalation)
     │
     ▼
  Event Bus (SSE)  ──▶  React + Vite Dashboard (live calls, transcripts, tickets, evals)
                              ▲
                              │
                          Cekura  ── automated red-team testing → self-improvement loop
```

In **MOCK_MODE** (default), the full pipeline runs with deterministic, simulated vendor responses so the product demos reliably without any API keys. Each adapter is structured for production with clearly marked `TODO(production)` wiring points.

## Sponsor Integration

- **Twilio** — `POST /twilio/voice` returns TwiML that connects inbound calls to a WebSocket media stream at `WS /twilio/media`, where Media Stream events (`connected`, `start`, `media`, `stop`) are handled.
- **Daily / Pipecat** — `PipecatMunicipalAgent` is the orchestration layer for each conversational turn; production pipeline frames (Twilio transport → Nova Sonic → tools) are documented inline.
- **AWS** — `AWSNovaSonicService` adapter targets Bedrock Nova Sonic speech-to-speech with `connect` / `stream_audio` / `generate_response` / `close`.
- **NVIDIA** — `NvidiaNimASRService` provides high-accuracy address transcription/verification via `transcribe_address`.
- **Cekura** — `CekuraClient` runs scenarios against the test framework and maps results into evaluation metrics that drive the self-improvement loop.
- **Y Combinator** — startup-grade product: cinematic landing page, live operator dashboard, and a measurable quality-improvement story.

---

## Folder Structure

```
municipal-311-assistant/
  README.md
  .env.example
  backend/
    requirements.txt
    server.py            # FastAPI app: health, calls, tickets, demo, evals, SSE
    bot.py               # standalone agent runner (terminal demo)
    test_agent.py        # CLI: trigger evals + show before/after improvement
    app/
      config.py          # env vars + MOCK_MODE
      models.py          # Pydantic models
      state.py           # in-memory demo store (seeded)
      events.py          # asyncio pub/sub event bus for SSE
      tools.py           # 311 city-service tool functions
      prompts.py         # system prompt + improvement playbook
      twilio_routes.py   # /twilio/voice + /twilio/media WebSocket
      cekura_client.py   # Cekura client + self-improvement loop
      services/
        nova_sonic.py    # AWSNovaSonicService adapter
        nvidia_nim.py    # NvidiaNimASRService adapter
        pipecat_agent.py # PipecatMunicipalAgent (deterministic demo routing)
  frontend/
    package.json, vite.config.ts, tailwind.config.js, ...
    src/
      App.tsx, main.tsx, index.css
      lib/{utils.ts, api.ts}
      components/
        Hero.tsx, Navbar.tsx, Dashboard.tsx
        ActiveCallPanel.tsx, TranscriptPanel.tsx, TicketTable.tsx
        ToolCallFeed.tsx, EvaluationLoop.tsx, SystemArchitecture.tsx
        MetricCard.tsx, SponsorStrip.tsx
        ui/{button,card,badge,tabs,table}.tsx
```

---

## Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 7860 --reload
```

The API is then at `http://localhost:7860` (interactive docs at `/docs`).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. In dev, Vite proxies `/api` and `/twilio` to the backend on port 7860, so no extra config is needed.

### Phone calls with ngrok + Twilio

```bash
ngrok http 7860
```

Then set `PUBLIC_BASE_URL` in your `.env` to the https ngrok domain and restart the backend.

In the Twilio console:
- Buy a phone number.
- Set the Voice webhook (A Call Comes In) to: `https://YOUR_NGROK_DOMAIN/twilio/voice`
- Ensure Twilio can reach the media stream at: `wss://YOUR_NGROK_DOMAIN/twilio/media`

### Evaluation

```bash
cd backend
python test_agent.py            # runs 2 evals, prints before/after improvement
python test_agent.py --runs 1   # single run
```

### Quick terminal demo (no frontend / no phone)

```bash
cd backend
python bot.py
```

---

## Environment Variables

| Variable | Purpose |
| --- | --- |
| `MOCK_MODE` | `true` runs everything simulated (default); `false` attempts real vendor calls |
| `PUBLIC_BASE_URL` | Public URL used to build the Twilio media-stream `wss://` URL |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | AWS Bedrock credentials |
| `AWS_REGION` | AWS region (default `us-east-1`) |
| `AWS_BEDROCK_MODEL_ID` | Nova Sonic model id |
| `NVIDIA_API_KEY` | NVIDIA NIM ASR key |
| `CEKURA_API_KEY` | Cekura test-framework key |
| `CEKURA_BASE_URL` | Cekura API base (default `https://api.cekura.ai`) |

---

## Hackathon Judging Demo Script

1. **Open the dashboard** (`npm run dev` → `http://localhost:5173`) and click *Launch Live Dashboard*.
2. **Start the backend** (`uvicorn server:app ... --port 7860`).
3. **Start the frontend** (already running) — metrics and seeded tickets load.
4. **Call the Twilio number** (or click *Start Demo Call*).
5. **Report a pothole** — *"There's a huge pothole on Market Street near 5th."*
6. **Show the ticket appears instantly** in the City Ticket Database with the tool call in the feed.
7. **Run the stress test** — click *Run Stress Test* to fire Cekura scenarios.
8. **Show the evaluation score and self-improvement loop** — the chart updates and a new prompt version appears with targeted guidance notes.

---

## Production Notes

This is a hackathon MVP optimized for demo reliability. To productionize:

- Replace the in-memory store (`app/state.py`) with a real database.
- Complete the `TODO(production)` SDK wiring in `nova_sonic.py`, `nvidia_nim.py`, and `cekura_client.py`.
- Wire the real Pipecat pipeline in `pipecat_agent.py` / `bot.py` (Twilio transport → Nova Sonic → tool processor).
- Add authentication to the API and lock down CORS.
- The self-improvement loop currently appends versioned prompt-guidance notes (safe and explainable); promote a human-in-the-loop review before deploying prompt changes.
