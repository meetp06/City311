import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  getEvalHistory,
  runEvaluation,
  type EvaluationResult,
  type PromptVersion,
} from "@/lib/api";
import { GitBranch, Loader2, Play, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const DIMENSIONS: { key: keyof EvaluationResult; label: string; pct: boolean; invert?: boolean }[] = [
  { key: "task_success_rate", label: "Task success", pct: true },
  { key: "address_capture_accuracy", label: "Address capture", pct: true },
  { key: "escalation_precision", label: "Escalation precision", pct: true },
  { key: "citizen_sentiment_score", label: "Citizen sentiment", pct: true },
  { key: "hallucination_rate", label: "Hallucination rate", pct: true, invert: true },
  { key: "average_latency_ms", label: "Avg latency", pct: false },
];

function fmt(d: (typeof DIMENSIONS)[number], r: EvaluationResult) {
  const v = r[d.key] as number;
  if (!d.pct) return `${v} ms`;
  return `${(v * 100).toFixed(1)}%`;
}

interface Props {
  onEvalComplete?: (result: EvaluationResult) => void;
}

export default function EvaluationLoop({ onEvalComplete }: Props = {}) {
  const [loading, setLoading] = useState(false);
  const [latest, setLatest] = useState<EvaluationResult | null>(null);
  const [history, setHistory] = useState<EvaluationResult[]>([]);
  const [versions, setVersions] = useState<PromptVersion[]>([]);

  async function refresh() {
    const h = await getEvalHistory();
    setHistory(h.history);
    setVersions(h.prompt_versions);
    if (h.history.length) setLatest(h.history[h.history.length - 1]);
  }

  useEffect(() => {
    refresh().catch(() => {});
  }, []);

  async function handleRun() {
    setLoading(true);
    try {
      const res = await runEvaluation();
      setLatest(res.result);
      setVersions(res.prompt_versions);
      onEvalComplete?.(res.result);
      await refresh();
    } finally {
      setLoading(false);
    }
  }

  const chartData = history.map((h, i) => ({
    name: `#${i + 1}`,
    score: Math.round(h.overall_score * 1000) / 10,
    version: h.prompt_version,
  }));

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-xl" style={{ fontFamily: "'Instrument Serif', serif" }}>
            Automated Voice Evaluation
          </h3>
          <p className="text-sm text-muted-foreground">
            Cekura red-team & regression scenarios. Weak dimensions trigger the self-improvement loop.
          </p>
        </div>
        <Button variant="glass" size="pill" onClick={handleRun} disabled={loading}>
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          {loading ? "Running stress test…" : "Run Stress Test"}
        </Button>
      </div>

      {/* Result cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {DIMENSIONS.map((d) => (
          <Card key={d.key} className="p-4">
            <div className="text-xs text-muted-foreground">{d.label}</div>
            <div className="mt-2 text-2xl" style={{ fontFamily: "'Instrument Serif', serif" }}>
              {latest ? fmt(d, latest) : "—"}
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        {/* Chart */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle>Overall Score Over Time</CardTitle>
            {latest && (
              <Badge variant="success">
                Overall {(latest.overall_score * 100).toFixed(1)}%
              </Badge>
            )}
          </CardHeader>
          <CardContent>
            <div className="h-[260px]">
              {chartData.length === 0 ? (
                <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                  Run a stress test to populate the chart.
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="name" stroke="rgba(255,255,255,0.4)" fontSize={12} />
                    <YAxis domain={[60, 100]} stroke="rgba(255,255,255,0.4)" fontSize={12} />
                    <Tooltip
                      contentStyle={{
                        background: "rgba(10,20,30,0.95)",
                        border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: 12,
                        color: "#fff",
                      }}
                      formatter={(v: number) => [`${v}%`, "Overall"]}
                    />
                    <Line
                      type="monotone"
                      dataKey="score"
                      stroke="#34d399"
                      strokeWidth={2.5}
                      dot={{ r: 3, fill: "#34d399" }}
                      activeDot={{ r: 5 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Prompt version timeline */}
        <Card>
          <CardHeader className="flex-row items-center gap-2">
            <GitBranch className="h-4 w-4 text-sky-300" />
            <CardTitle>Prompt Versions</CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="relative ml-2 space-y-4 border-l border-white/10 pl-4">
              {versions.map((v, i) => (
                <li key={v.version} className="relative">
                  <span className="absolute -left-[22px] top-1 flex h-3 w-3 items-center justify-center rounded-full bg-sky-400/30">
                    <span className="h-1.5 w-1.5 rounded-full bg-sky-300" />
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm">{v.version}</span>
                    {i === versions.length - 1 && <Badge variant="info">current</Badge>}
                    {i > 0 && <Sparkles className="h-3 w-3 text-amber-300" />}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{v.notes}</p>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
