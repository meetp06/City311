// API client for the dashboard.
// All data comes from the real FastAPI backend at /api/* (Vite proxy → :7861).
// The backend is populated live by webhooks from the cloud bot during calls.

export interface Ticket {
  ticket_id: string;
  category: string;
  location: string;
  description: string;
  status: string;
  priority: string;
  created_at: string;
}

export interface Call {
  call_id: string;
  caller_phone: string;
  status: string;
  language: string;
  intent: string;
  sentiment: string;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number;
}

export interface ToolCall {
  tool: string;
  args: Record<string, unknown>;
  result: Record<string, unknown>;
  status: string;
  timestamp: string;
}

export interface EvaluationResult {
  run_id: string;
  task_success_rate: number;
  address_capture_accuracy: number;
  escalation_precision: number;
  average_latency_ms: number;
  citizen_sentiment_score: number;
  hallucination_rate: number;
  overall_score: number;
  prompt_version: string;
  created_at: string;
}

export interface PromptVersion {
  version: string;
  notes: string;
  created_at: string;
}

export interface DashboardEvent {
  type: string;
  data: any;
  ts: string;
}

// ── Mock Data (DISABLED) ───────────────────────────────────────
// All seeded demo data removed. Dashboard now reflects only real bot activity.
// Kept previously unused MOCK_* constants are deleted below to avoid confusion.

// ── API Functions (real integration) ───────────────────────────
//
// Base URL is read from the VITE_API_BASE_URL env var at build time.
// - In local dev, leave it empty so requests stay relative and the Vite
//   proxy forwards /api and /twilio to http://localhost:7861.
// - On Vercel, set VITE_API_BASE_URL to the ngrok HTTPS URL that
//   exposes the FastAPI backend (e.g. https://<your>.ngrok-free.dev).
// Trailing slashes are stripped so callers can use leading-slash paths.
const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");
const api = (path: string) => `${API_BASE}${path}`;

export async function getTickets(): Promise<Ticket[]> {
  const res = await fetch(api("/api/tickets"));
  if (!res.ok) throw new Error("Failed to fetch tickets");
  const data = await res.json();
  return data.tickets;
}

export async function getCalls(): Promise<{ active: Call[]; recent: Call[] }> {
  const res = await fetch(api("/api/calls"));
  if (!res.ok) throw new Error("Failed to fetch calls");
  const data = await res.json();
  return data;
}

export async function getToolCalls(): Promise<ToolCall[]> {
  const res = await fetch(api("/api/tool-calls"));
  if (!res.ok) throw new Error("Failed to fetch tool calls");
  const data = await res.json();
  return data.tool_calls;
}

export async function runEvaluation(): Promise<{
  result: EvaluationResult;
  prompt_versions: PromptVersion[];
}> {
  const res = await fetch(api("/api/evals/run"), { method: "POST" });
  if (!res.ok) throw new Error("Failed to run evaluation");
  return await res.json();
}

export async function getEvalHistory(): Promise<{
  history: EvaluationResult[];
  prompt_versions: PromptVersion[];
}> {
  const res = await fetch(api("/api/evals/history"));
  if (!res.ok) throw new Error("Failed to fetch evaluation history");
  return await res.json();
}

export async function startDemoCall(caller_phone?: string): Promise<{ call: Call }> {
  const res = await fetch(api("/api/demo/start-call"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ caller_phone }),
  });
  if (!res.ok) throw new Error("Failed to start demo call");
  return await res.json();
}

export async function endDemoCall(call_id?: string) {
  const res = await fetch(api("/api/demo/end-call"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ call_id }),
  });
  if (!res.ok) throw new Error("Failed to end demo call");
  return await res.json();
}

export async function sendDemoTranscript(
  text: string,
  call_id?: string,
  caller_phone?: string
) {
  const res = await fetch(api("/api/demo/transcript"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, call_id, caller_phone }),
  });
  if (!res.ok) throw new Error("Failed to send transcript");
  return await res.json();
}

export function subscribeToEvents(onEvent: (e: DashboardEvent) => void): () => void {
  const eventSource = new EventSource(api("/api/events/stream"));
  eventSource.onmessage = (event) => {
    try {
      const parsed = JSON.parse(event.data);
      if (parsed.type && parsed.type !== "connected") {
        onEvent(parsed);
      }
    } catch (err) {
      console.error("Error parsing event data:", err);
    }
  };
  eventSource.onerror = (err) => {
    console.error("SSE connection error:", err);
  };
  return () => {
    eventSource.close();
  };
}
