import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn, formatTime } from "@/lib/utils";
import { Bot, User } from "lucide-react";
import { useEffect, useRef } from "react";

export interface TranscriptItem {
  role: "citizen" | "assistant";
  text: string;
  ts: string;
}

export default function TranscriptPanel({ lines }: { lines: TranscriptItem[] }) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  return (
    <Card className="flex h-full flex-col">
      <CardHeader>
        <CardTitle>Live Transcript</CardTitle>
      </CardHeader>
      <CardContent className="flex-1">
        <div className="scroll-thin flex max-h-[360px] min-h-[200px] flex-col gap-3 overflow-y-auto pr-1">
          {lines.length === 0 && (
            <p className="text-sm text-muted-foreground">Transcript will appear here in real time.</p>
          )}
          {lines.map((line, i) => {
            const isAssistant = line.role === "assistant";
            return (
              <div
                key={i}
                className={cn("flex gap-2", isAssistant ? "flex-row" : "flex-row-reverse")}
              >
                <div
                  className={cn(
                    "flex h-7 w-7 shrink-0 items-center justify-center rounded-full",
                    isAssistant ? "bg-sky-400/15 text-sky-300" : "bg-white/10 text-foreground"
                  )}
                >
                  {isAssistant ? <Bot className="h-4 w-4" /> : <User className="h-4 w-4" />}
                </div>
                <div
                  className={cn(
                    "max-w-[78%] rounded-2xl px-3.5 py-2 text-sm",
                    isAssistant
                      ? "rounded-tl-sm bg-white/[0.04] text-foreground"
                      : "rounded-tr-sm bg-sky-500/15 text-foreground"
                  )}
                >
                  <div className="mb-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                    {isAssistant ? "Assistant" : "Citizen"} · {formatTime(line.ts)}
                  </div>
                  {line.text}
                </div>
              </div>
            );
          })}
          <div ref={endRef} />
        </div>
      </CardContent>
    </Card>
  );
}
