import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

export default function MetricCard({
  label,
  value,
  icon: Icon,
  hint,
  trend,
}: {
  label: string;
  value: string;
  icon: LucideIcon;
  hint?: string;
  trend?: "up" | "down" | "flat";
}) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between">
        <span className="text-sm text-muted-foreground">{label}</span>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="mt-3 text-3xl font-normal tracking-tight" style={{ fontFamily: "'Instrument Serif', serif" }}>
        {value}
      </div>
      {hint && (
        <div
          className={cn(
            "mt-1 text-xs",
            trend === "up" && "text-emerald-300",
            trend === "down" && "text-red-300",
            (!trend || trend === "flat") && "text-muted-foreground"
          )}
        >
          {hint}
        </div>
      )}
    </Card>
  );
}
