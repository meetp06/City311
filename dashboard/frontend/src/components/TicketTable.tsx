import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatTime } from "@/lib/utils";
import type { Ticket } from "@/lib/api";
import { motion } from "framer-motion";

function priorityVariant(p: string) {
  switch (p) {
    case "urgent":
      return "danger" as const;
    case "high":
      return "warning" as const;
    case "low":
      return "muted" as const;
    default:
      return "info" as const;
  }
}

function statusVariant(s: string) {
  switch (s) {
    case "escalated":
      return "danger" as const;
    case "resolved":
      return "success" as const;
    case "in_progress":
      return "info" as const;
    default:
      return "muted" as const;
  }
}

export default function TicketTable({ tickets, highlightId }: { tickets: Ticket[]; highlightId?: string }) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>City Ticket Database</CardTitle>
        <Badge variant="muted">{tickets.length} tickets</Badge>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Ticket ID</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Location</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tickets.map((t) => (
              <motion.tr
                key={t.ticket_id}
                initial={t.ticket_id === highlightId ? { backgroundColor: "rgba(56,189,248,0.18)" } : false}
                animate={{ backgroundColor: "rgba(56,189,248,0)" }}
                transition={{ duration: 2.4 }}
                className="border-b border-white/5"
              >
                <TableCell className="font-mono text-xs">{t.ticket_id}</TableCell>
                <TableCell>{t.category}</TableCell>
                <TableCell className="max-w-[220px] truncate text-muted-foreground">{t.location}</TableCell>
                <TableCell><Badge variant={priorityVariant(t.priority)}>{t.priority}</Badge></TableCell>
                <TableCell><Badge variant={statusVariant(t.status)}>{t.status.replace("_", " ")}</Badge></TableCell>
                <TableCell className="text-xs text-muted-foreground">{formatTime(t.created_at)}</TableCell>
              </motion.tr>
            ))}
            {tickets.length === 0 && (
              <TableRow>
                <TableCell className="py-6 text-center text-muted-foreground" colSpan={6}>
                  No tickets yet.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
