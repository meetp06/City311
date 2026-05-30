import { Button } from "@/components/ui/button";

const NAV_LINKS = [
  { label: "Home", href: "#home", active: true },
  { label: "Dashboard", href: "#dashboard" },
  { label: "Voice Agent", href: "#voice-agent" },
  { label: "Evaluation", href: "#evaluation" },
  { label: "Architecture", href: "#architecture" },
];

export default function Navbar({ onLaunch }: { onLaunch: () => void }) {
  return (
    <nav className="relative z-10 mx-auto flex max-w-7xl items-center justify-between px-8 py-6">
      <a
        href="#home"
        className="text-3xl tracking-tight text-foreground"
        style={{ fontFamily: "'Instrument Serif', serif" }}
      >
        City311<sup className="text-xs">®</sup>
      </a>

      <div className="hidden items-center gap-8 md:flex">
        {NAV_LINKS.map((link) => (
          <a
            key={link.label}
            href={link.href}
            className={
              link.active
                ? "text-sm text-foreground transition-colors"
                : "text-sm text-muted-foreground transition-colors hover:text-foreground"
            }
          >
            {link.label}
          </a>
        ))}
      </div>

      <Button
        variant="glass"
        className="rounded-full px-6 py-2.5 text-sm text-foreground hover:scale-[1.03]"
        onClick={onLaunch}
      >
        Launch Demo
      </Button>
    </nav>
  );
}
