import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatTime } from "@/lib/utils";
import { Wrench } from "lucide-react";

export interface ToolCallItem {
  tool: string;
  status: string;
  ts: string;
  summary?: string;
}

export default function ToolCallFeed({ calls }: { calls: ToolCallItem[] }) {
  return (
    <Card className="flex h-full flex-col">
      <CardHeader>
        <CardTitle>Tool Call Feed</CardTitle>
      </CardHeader>
      <CardContent className="flex-1">
        <div className="scroll-thin flex max-h-[360px] flex-col gap-2 overflow-y-auto pr-1">
          {calls.length === 0 && (
            <p className="text-sm text-muted-foreground">Function calls will stream here as the agent acts.</p>
          )}
          {calls.map((c, i) => (
            <div
              key={i}
              className="flex items-center justify-between rounded-xl bg-white/[0.03] px-3 py-2.5"
            >
              <div className="flex items-center gap-2.5">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-white/5">
                  <Wrench className="h-3.5 w-3.5 text-sky-300" />
                </div>
                <div>
                  <div className="font-mono text-xs text-foreground">{c.tool}</div>
                  {c.summary && <div className="text-[11px] text-muted-foreground">{c.summary}</div>}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={c.status === "success" ? "success" : "danger"}>{c.status}</Badge>
                <span className="text-[11px] text-muted-foreground">{formatTime(c.ts)}</span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
