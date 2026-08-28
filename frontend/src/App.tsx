import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { Moon, ScanEye, Sun } from "lucide-react";
import { getHealth } from "./lib/api";
import { cn } from "./lib/ui";
import { Home } from "./pages/Home";
import { History } from "./pages/History";
import { ModelCard } from "./pages/ModelCard";

function useTheme() {
  const [dark, setDark] = useState(() => localStorage.getItem("santhra-theme") !== "light");
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("santhra-theme", dark ? "dark" : "light");
  }, [dark]);
  return { dark, toggle: () => setDark((d) => !d) };
}

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
    const t = setInterval(check, 15000); // poll so recovery/failure is reflected
    return () => { alive = false; clearInterval(t); };
  }, []);
  const meta: Record<HealthState, { color: string; label: string }> = {
    loading: { color: "bg-slate-400", label: "…" },
    healthy: { color: "bg-emerald-500", label: "API online" },
    degraded: { color: "bg-amber-500", label: "API degraded" },
    offline: { color: "bg-rose-500", label: "API offline" },
  };
  const m = meta[state];
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-slate-400">
      <span className={cn("h-2 w-2 rounded-full", m.color, state === "healthy" && "animate-pulse")} />
      {m.label}
    </span>
  );
}

export default function App() {
  const { dark, toggle } = useTheme();
  const link = (isActive: boolean) => cn(
    "rounded-lg px-3 py-1.5 text-sm font-medium transition",
    isActive ? "bg-brand-500/15 text-brand-500 dark:text-brand-300"
      : "text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white",
  );

  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-30 border-b border-slate-200/70 bg-white/70 backdrop-blur-xl dark:border-white/10 dark:bg-slate-950/50">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2.5">
            <div className="rounded-xl bg-gradient-to-br from-brand-500 to-sky-500 p-2 shadow-lg shadow-brand-600/30">
              <ScanEye className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="text-sm font-bold leading-tight">Santhra</p>
              <p className="text-[10px] uppercase tracking-widest text-slate-400">Visual Quality Intelligence</p>
            </div>
          </div>
          <nav className="flex items-center gap-1">
            <NavLink to="/" className={({ isActive }) => link(isActive)}>Analyze</NavLink>
            <NavLink to="/history" className={({ isActive }) => link(isActive)}>History</NavLink>
            <NavLink to="/model" className={({ isActive }) => link(isActive)}>Model</NavLink>
            <span className="mx-2 hidden sm:block"><HealthDot /></span>
            <button onClick={toggle} aria-label="Toggle theme"
              className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-white/10">
              {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/history" element={<History />} />
          <Route path="/model" element={<ModelCard />} />
        </Routes>
      </main>

      <footer className="mx-auto max-w-6xl px-4 py-8 text-center text-xs text-slate-400">
        Santhra · Hybrid CV + deep-learning image-quality inspection · runs fully local, no external AI.
      </footer>
    </div>
  );
}
