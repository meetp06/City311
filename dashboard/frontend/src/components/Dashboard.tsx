import { useEffect, useState } from "react";
import { Activity, AlertTriangle, Clock, Gauge, PhoneCall, Ticket as TicketIcon } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card } from "@/components/ui/card";
import MetricCard from "./MetricCard";
import ActiveCallPanel from "./ActiveCallPanel";
import TranscriptPanel, { type TranscriptItem } from "./TranscriptPanel";
import TicketTable from "./TicketTable";
import ToolCallFeed, { type ToolCallItem } from "./ToolCallFeed";
import EvaluationLoop from "./EvaluationLoop";
import {
  getCalls,
  getTickets,
  getToolCalls,
  subscribeToEvents,
  type Call,
  type EvaluationResult,
  type Ticket,
} from "@/lib/api";

function summarizeTool(tool: string, args: Record<string, unknown>): string {
  const loc = (args.location || args.address || args.reason || "") as string;
  return loc ? String(loc).slice(0, 40) : "";
}

// Live transcript starts empty — populated by real bot transcripts via SSE.

export default function Dashboard() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [call, setCall] = useState<Call | null>(null);
  const [toolCalls, setToolCalls] = useState<ToolCallItem[]>([]);
  const [transcript, setTranscript] = useState<TranscriptItem[]>([]);
  const [latestEval, setLatestEval] = useState<EvaluationResult | null>(null);
  const [highlightId] = useState<string>();

  useEffect(() => {
    getTickets().then(setTickets).catch(() => {});
    getToolCalls()
      .then((tc) =>
        setToolCalls(
          tc.map((c) => ({ tool: c.tool, status: c.status, ts: c.timestamp, summary: summarizeTool(c.tool, c.args) }))
        )
      )
      .catch(() => {});
    getCalls()
      .then((c) => {
        const activeCall = c.active[0] || c.recent[0];
        setCall(activeCall ?? null);
        if (activeCall && activeCall.transcript && activeCall.transcript.length > 0) {
          setTranscript(
            activeCall.transcript.map((line: any) => ({
              role: line.role,
              text: line.text,
              ts: line.timestamp,
            }))
          );
        }
      })
      .catch(() => {});

    // SSE Event Subscription
    const unsubscribe = subscribeToEvents((event) => {
      const { type, data } = event;
      if (type === "call_started") {
        setCall(data);
        setTranscript([]);
      } else if (type === "transcript_added") {
        setTranscript((prev) => [
          ...prev,
          { role: data.role, text: data.text, ts: data.timestamp || new Date().toISOString() },
        ]);
      } else if (type === "ticket_created") {
        setTickets((prev) => [data, ...prev]);
      } else if (type === "tool_called") {
        setToolCalls((prev) => [
          {
            tool: data.tool,
            status: data.status,
            ts: data.timestamp || new Date().toISOString(),
            summary: summarizeTool(data.tool, data.args || {}),
          },
          ...prev,
        ]);
      } else if (type === "call_ended") {
        setCall((prev) => (prev && prev.call_id === data.call_id ? { ...prev, status: "ended", ended_at: new Date().toISOString() } : prev));
      }
    });

    return () => {
      unsubscribe();
    };
  }, []);

  const activeCalls = call?.status === "active" ? 1 : 0;
  const escAccuracy = latestEval ? `${(latestEval.escalation_precision * 100).toFixed(0)}%` : "—";
  const hallucination = latestEval ? `${(latestEval.hallucination_rate * 100).toFixed(1)}%` : "—";
  const evalScore = latestEval ? `${(latestEval.overall_score * 100).toFixed(0)}%` : "—";
  const avgLatency = latestEval ? `${latestEval.average_latency_ms}ms` : "—";

  return (
    <section id="dashboard" className="mx-auto max-w-7xl px-6 py-16">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-3xl sm:text-4xl" style={{ fontFamily: "'Instrument Serif', serif" }}>
            Operator Dashboard
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Live view of calls, transcripts, tickets, tool calls, and evaluation metrics.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/[0.06] px-4 py-1.5 text-xs text-emerald-300">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 pulse-ring" />
          System Online
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        <MetricCard label="Active Calls" value={String(activeCalls)} icon={PhoneCall} hint="real-time" />
        <MetricCard label="Tickets Filed" value={String(tickets.length)} icon={TicketIcon} hint="this session" trend="up" />
        <MetricCard label="Avg Response" value={avgLatency} icon={Clock} hint="speech-to-speech" />
        <MetricCard label="Eval Score" value={evalScore} icon={Gauge} hint="Cekura latest" trend="up" />
        <MetricCard label="Escalation Acc." value={escAccuracy} icon={Activity} hint="precision" />
        <MetricCard label="Hallucination" value={hallucination} icon={AlertTriangle} hint="lower is better" trend="down" />
      </div>

      {/* Live panels */}
      <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-3">
        <ActiveCallPanel call={call} />
        <div className="lg:col-span-2">
          <TranscriptPanel lines={transcript} />
        </div>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <TicketTable tickets={tickets} highlightId={highlightId} />
        </div>
        <ToolCallFeed calls={toolCalls} />
      </div>

      {/* Evaluation */}
      <div id="evaluation" className="mt-10">
        <Tabs defaultValue="evaluation">
          <TabsList>
            <TabsTrigger value="evaluation">Evaluation Loop</TabsTrigger>
            <TabsTrigger value="overview">Session Overview</TabsTrigger>
          </TabsList>
          <TabsContent value="evaluation" className="mt-5">
            <EvaluationLoop onEvalComplete={setLatestEval} />
          </TabsContent>
          <TabsContent value="overview" className="mt-5">
            <Card className="p-6 text-sm text-muted-foreground">
              {tickets.length} tickets filed · {toolCalls.length} tool calls executed ·{" "}
              {transcript.length} transcript lines this session.
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </section>
  );
}
