import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { getHealth } from "./lib/api";
import { cn } from "./lib/ui";
import { Home } from "./pages/Home";
import { History } from "./pages/History";
import { ModelCard } from "./pages/ModelCard";

type HealthState = "loading" | "healthy" | "degraded" | "offline";

function HealthDot() {
  const [state, setState] = useState<HealthState>("loading");
  useEffect(() => {
    let alive = true;
    const check = () =>
      getHealth()
        .then((h) => alive && setState(h.status === "healthy" ? "healthy" : "degraded"))
        .catch(() => alive && setState("offline"));
    check();
    const t = setInterval(check, 15000);
    return () => { alive = false; clearInterval(t); };
  }, []);
  const meta: Record<HealthState, { color: string; label: string }> = {
    loading: { color: "bg-muted", label: "checking" },
    healthy: { color: "bg-sage", label: "online" },
    degraded: { color: "bg-ochre", label: "degraded" },
    offline: { color: "bg-danger", label: "offline" },
  };
  const m = meta[state];
  return (
    <span className="hidden items-center gap-2 rounded-full border border-line bg-surface px-3 py-1.5 sm:inline-flex">
      <span className={cn("h-2 w-2 rounded-full", m.color, state === "healthy" && "animate-pulse")} />
      <span className="eyebrow !text-muted !tracking-[0.15em]">{m.label}</span>
    </span>
  );
}

const TICKER = [
  "Hybrid CV + deep learning", "Calibrated confidence", "Grad-CAM heatmaps",
  "Runs fully local", "7 issue types", "Anomaly detection", "Signal agreement", "No API keys",
];

function Ticker() {
  const row = (
    <div className="marquee-track">
      {[...TICKER, ...TICKER].map((t, i) => (
        <span key={i} className="eyebrow !text-muted mx-5 inline-flex items-center gap-5">
          {t} <span className="text-clay">*</span>
        </span>
      ))}
    </div>
  );
  return (
    <div className="marquee overflow-hidden border-y border-line bg-paper-2 py-2.5">{row}</div>
  );
}

export default function App() {
  const nav = ({ isActive }: { isActive: boolean }) => cn(
    "text-sm font-medium transition-colors",
    isActive ? "text-ink" : "text-muted hover:text-ink",
  );

  return (
    <div className="flex min-h-full flex-col">
      <header className="sticky top-0 z-30 border-b border-line bg-paper/85 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
          <NavLink to="/" className="group flex items-baseline gap-2">
            <span className="font-display text-2xl font-semibold leading-none text-ink">Santhra</span>
            <span className="hidden text-clay sm:inline">*</span>
          </NavLink>
          <nav className="flex items-center gap-6">
            <NavLink to="/" end className={nav}>Analyze</NavLink>
            <NavLink to="/history" className={nav}>History</NavLink>
            <NavLink to="/model" className={nav}>Model</NavLink>
            <HealthDot />
            <NavLink to="/" className="btn btn-ink px-4 py-2 text-sm">Analyze image</NavLink>
          </nav>
        </div>
      </header>

      <Ticker />

      <main className="mx-auto w-full max-w-6xl flex-1 px-5 py-10">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/history" element={<History />} />
          <Route path="/model" element={<ModelCard />} />
        </Routes>
      </main>

      <footer className="mt-10 bg-forest text-paper">
        <div className="mx-auto grid max-w-6xl gap-8 px-6 py-12 sm:grid-cols-2 lg:grid-cols-4">
          <div className="lg:col-span-2">
            <p className="font-display text-2xl font-semibold">Santhra</p>
            <p className="mt-3 max-w-sm text-sm leading-relaxed text-paper/70">
              Hybrid computer-vision and deep-learning image quality inspection. See the
              signal, understand the evidence. Runs fully local, no external AI.
            </p>
            <span className="mt-4 inline-flex rounded-full border border-paper/25 px-3 py-1 eyebrow !text-clay-soft">
              Visual Quality Intelligence
            </span>
          </div>
          <div>
            <p className="eyebrow !text-paper/50">Explore</p>
            <ul className="mt-3 space-y-2 text-sm text-paper/80">
              <li><NavLink to="/" className="hover:text-white">Analyze</NavLink></li>
              <li><NavLink to="/history" className="hover:text-white">History</NavLink></li>
              <li><NavLink to="/model" className="hover:text-white">Model card</NavLink></li>
            </ul>
          </div>
          <div>
            <p className="eyebrow !text-paper/50">Detects</p>
            <ul className="mt-3 space-y-2 text-sm text-paper/80">
              <li>Blur, exposure, noise</li>
              <li>Contrast, compression</li>
              <li>Colour cast, anomalies</li>
            </ul>
          </div>
        </div>
        <div className="border-t border-paper/10">
          <p className="mx-auto max-w-6xl px-6 py-5 text-xs text-paper/50">
            Santhra * hybrid CV + deep-learning image-quality inspection * measured, learned and fused values, always shown together.
          </p>
        </div>
      </footer>
    </div>
  );
}
