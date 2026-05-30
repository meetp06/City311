import { Phone } from "lucide-react";
import Navbar from "./Navbar";

const VIDEO_SRC =
  "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260314_131748_f2ca2a28-fed7-44c8-b9a9-bd9acdd5ec31.mp4";

export default function Hero({ onLaunch }: { onLaunch: () => void }) {
  return (
    <section id="home" className="relative min-h-screen w-full overflow-hidden">
      {/* Fullscreen looping background video */}
      <video
        autoPlay
        loop
        muted
        playsInline
        className="absolute inset-0 z-0 h-full w-full object-cover"
      >
        <source src={VIDEO_SRC} type="video/mp4" />
      </video>

      {/* Subtle scrim only where text sits, for readability */}
      <div className="pointer-events-none absolute inset-0 z-[1] bg-gradient-to-b from-black/30 via-black/10 to-black/40" />

      <Navbar onLaunch={onLaunch} />

      <div className="relative z-10 flex flex-col items-center px-6 pb-40 pt-32 text-center">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/[0.06] px-4 py-1.5 text-xs text-emerald-300 backdrop-blur-sm">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 pulse-ring" />
          Live on Pipecat Cloud · YC Voice Agents Hackathon
        </div>

        <h1
          className="animate-fade-rise max-w-7xl text-5xl font-normal leading-[0.95] tracking-[-2.46px] sm:text-7xl md:text-8xl"
          style={{ fontFamily: "'Instrument Serif', serif" }}
        >
          Where <em className="not-italic text-muted-foreground">city services</em> answer{" "}
          <em className="not-italic text-muted-foreground">instantly.</em>
        </h1>

        <p className="animate-fade-rise-delay mt-8 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
          An AI-powered 311 voice assistant that answers calls, files city service tickets,
          escalates emergencies, and improves itself through automated voice testing.
        </p>

        {/* Phone CTA */}
        <div className="animate-fade-rise-delay-2 mt-10 flex flex-col items-center gap-3">
          <a
            href="tel:+19564764454"
            className="liquid-glass flex items-center gap-3 rounded-full px-8 py-4 text-lg text-foreground transition-transform hover:scale-[1.03]"
          >
            <Phone className="h-5 w-5 text-emerald-400" />
            <span style={{ fontFamily: "'Instrument Serif', serif" }}>
              (956) 476-4454
            </span>
          </a>
          <span className="text-xs text-muted-foreground">Call now to try City311</span>
        </div>

        <button
          onClick={onLaunch}
          className="animate-fade-rise-delay-2 mt-6 cursor-pointer rounded-full border border-white/10 bg-white/[0.03] px-10 py-3 text-sm text-muted-foreground backdrop-blur-sm transition-all hover:border-white/20 hover:text-foreground"
        >
          View Dashboard ↓
        </button>
      </div>
    </section>
  );
}
