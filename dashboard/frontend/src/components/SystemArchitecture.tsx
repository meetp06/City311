import { Card } from "@/components/ui/card";
import {
  ArrowRight,
  Cpu,
  Database,
  Mic,
  PhoneCall,
  Server,
  ShieldCheck,
  Volume2,
  Workflow,
} from "lucide-react";

const PIPELINE = [
  { label: "Citizen Phone", icon: PhoneCall, note: "Inbound call" },
  { label: "Twilio", icon: PhoneCall, note: "Media Streams" },
  { label: "Pipecat Cloud", icon: Workflow, note: "Realtime orchestration" },
  { label: "Gradium STT", icon: Mic, note: "Speech-to-text" },
  { label: "Nemotron LLM", icon: Cpu, note: "NVIDIA 120B reasoning" },
  { label: "Gradium TTS", icon: Volume2, note: "Text-to-speech" },
  { label: "311 Tools", icon: Database, note: "Tickets & lookups" },
];

export default function SystemArchitecture() {
  return (
    <section id="architecture" className="mx-auto max-w-7xl px-6 py-16">
      <h2 className="text-3xl sm:text-4xl" style={{ fontFamily: "'Instrument Serif', serif" }}>
        System Architecture
      </h2>
      <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
        Real-time voice pipeline from the phone network through Pipecat Cloud, powered by
        NVIDIA Nemotron-3-Super-120B and Gradium for speech services.
      </p>

      <Card className="mt-8 p-6">
        <div className="flex flex-col gap-3 lg:flex-row lg:flex-wrap lg:items-stretch">
          {PIPELINE.map((step, i) => (
            <div key={step.label} className="flex items-center gap-3">
              <div className="flex min-w-[150px] flex-col rounded-xl bg-white/[0.04] px-4 py-3">
                <step.icon className="h-5 w-5 text-sky-300" />
                <span className="mt-2 text-sm font-medium">{step.label}</span>
                <span className="text-[11px] text-muted-foreground">{step.note}</span>
              </div>
              {i < PIPELINE.length - 1 && (
                <ArrowRight className="hidden h-4 w-4 shrink-0 text-muted-foreground lg:block" />
              )}
            </div>
          ))}
        </div>

        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          <div className="flex items-start gap-3 rounded-xl border border-emerald-400/20 bg-emerald-400/[0.04] px-4 py-3">
            <Cpu className="mt-0.5 h-5 w-5 text-emerald-300" />
            <div>
              <div className="text-sm font-medium">NVIDIA Nemotron</div>
              <div className="text-xs text-muted-foreground">
                120B parameter model for high-accuracy reasoning, tool calling, and city-service intelligence.
              </div>
            </div>
          </div>
          <div className="flex items-start gap-3 rounded-xl border border-sky-400/20 bg-sky-400/[0.04] px-4 py-3">
            <Server className="mt-0.5 h-5 w-5 text-sky-300" />
            <div>
              <div className="text-sm font-medium">Pipecat + Daily</div>
              <div className="text-xs text-muted-foreground">
                Open-source voice AI framework with cloud deployment, Krisp noise cancellation, and WebRTC transport.
              </div>
            </div>
          </div>
          <div className="flex items-start gap-3 rounded-xl border border-amber-400/20 bg-amber-400/[0.04] px-4 py-3">
            <ShieldCheck className="mt-0.5 h-5 w-5 text-amber-300" />
            <div>
              <div className="text-sm font-medium">Cekura</div>
              <div className="text-xs text-muted-foreground">
                Automated voice testing with 5 scenarios, 11 metrics, and continuous evaluation.
              </div>
            </div>
          </div>
        </div>
      </Card>
    </section>
  );
}
