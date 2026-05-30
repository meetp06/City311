import { useRef } from "react";
import Hero from "./components/Hero";
import Dashboard from "./components/Dashboard";
import SystemArchitecture from "./components/SystemArchitecture";
import SponsorStrip from "./components/SponsorStrip";

export default function App() {
  const dashboardRef = useRef<HTMLDivElement>(null);

  const scrollToDashboard = () => {
    document.getElementById("dashboard")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Hero onLaunch={scrollToDashboard} />
      <div ref={dashboardRef}>
        <Dashboard />
      </div>
      <SystemArchitecture />
      <SponsorStrip />
      <footer className="border-t border-white/5 py-8 text-center text-xs text-muted-foreground">
        City311® — Municipal Voice Assistant · YC Voice Agents Hackathon demo
      </footer>
    </div>
  );
}
