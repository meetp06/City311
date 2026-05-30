import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Phone, PhoneOff } from "lucide-react";
import type { Call } from "@/lib/api";
import { useEffect, useState } from "react";

function sentimentVariant(s: string) {
  if (s === "frustrated") return "danger" as const;
  if (s === "positive") return "success" as const;
  return "muted" as const;
}

export default function ActiveCallPanel({ call }: { call: Call | null }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!call || call.status !== "active") return;
    const start = new Date(call.started_at).getTime();
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(id);
  }, [call]);

  const mins = String(Math.floor(elapsed / 60)).padStart(2, "0");
  const secs = String(elapsed % 60).padStart(2, "0");
  const active = call?.status === "active";

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Active Call</CardTitle>
        {active ? (
          <span className="flex items-center gap-2 text-xs text-emerald-300">
            <span className="pulse-ring inline-block h-2 w-2 rounded-full bg-emerald-400" />
            Live
          </span>
        ) : (
          <span className="flex items-center gap-2 text-xs text-muted-foreground">
            <PhoneOff className="h-3.5 w-3.5" /> No active call
          </span>
        )}
      </CardHeader>
      <CardContent>
        {call ? (
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/5">
                <Phone className="h-4 w-4 text-foreground" />
              </div>
              <div>
                <div className="font-medium">{call.caller_phone}</div>
                <div className="text-xs text-muted-foreground">Call {call.call_id}</div>
              </div>
            </div>

            <dl className="grid grid-cols-2 gap-3 text-sm">
              <Field label="Status">
                <Badge variant={active ? "success" : "muted"}>{call.status}</Badge>
              </Field>
              <Field label="Language">{call.language}</Field>
              <Field label="Detected intent">
                <span className="text-foreground">{call.intent}</span>
              </Field>
              <Field label="Sentiment">
                <Badge variant={sentimentVariant(call.sentiment)}>{call.sentiment}</Badge>
              </Field>
              <Field label="Duration">
                <span className="tabular-nums">{mins}:{secs}</span>
              </Field>
            </dl>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            Start a demo call or dial the Twilio number to see live call telemetry here.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1">{children}</dd>
    </div>
  );
}
