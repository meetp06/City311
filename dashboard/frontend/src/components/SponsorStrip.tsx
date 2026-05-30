const BUILT_WITH = [
  { name: "NVIDIA", note: "Nemotron 120B LLM" },
  { name: "Pipecat", note: "Voice AI Framework" },
  { name: "Daily", note: "WebRTC Transport" },
  { name: "Twilio", note: "Phone Network" },
  { name: "Gradium", note: "STT & TTS" },
  { name: "Cekura", note: "Voice Testing" },
];

export default function SponsorStrip() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-12">
      <p className="text-center text-xs uppercase tracking-[0.25em] text-muted-foreground">
        Built with
      </p>
      <div className="mt-6 flex flex-wrap items-center justify-center gap-x-8 gap-y-4">
        {BUILT_WITH.map((s) => (
          <div key={s.name} className="flex flex-col items-center gap-1">
            <span
              className="text-lg text-foreground/80 transition-colors hover:text-foreground"
              style={{ fontFamily: "'Instrument Serif', serif" }}
            >
              {s.name}
            </span>
            <span className="text-[10px] text-muted-foreground">{s.note}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
