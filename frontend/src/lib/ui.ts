export function cn(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

export function titleCase(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Returns tailwind text/bg/ring classes keyed to a 0-100 quality score. */
export function scoreTheme(score: number): { text: string; ring: string; bg: string; label: string } {
  if (score >= 90) return { text: "text-emerald-400", ring: "stroke-emerald-400", bg: "bg-emerald-500/10", label: "Excellent" };
  if (score >= 75) return { text: "text-green-400", ring: "stroke-green-400", bg: "bg-green-500/10", label: "Acceptable" };
  if (score >= 50) return { text: "text-amber-400", ring: "stroke-amber-400", bg: "bg-amber-500/10", label: "Degraded" };
  return { text: "text-rose-400", ring: "stroke-rose-400", bg: "bg-rose-500/10", label: "Potentially defective" };
}

export function severityTheme(sev: string): string {
  switch (sev) {
    case "CRITICAL": return "text-rose-300 bg-rose-500/15 ring-rose-500/30";
    case "HIGH": return "text-orange-300 bg-orange-500/15 ring-orange-500/30";
    case "MEDIUM": return "text-amber-300 bg-amber-500/15 ring-amber-500/30";
    default: return "text-sky-300 bg-sky-500/15 ring-sky-500/30";
  }
}

export function confidenceTheme(level: string): string {
  switch (level) {
    case "HIGH": return "text-emerald-300 bg-emerald-500/15 ring-emerald-500/30";
    case "MEDIUM": return "text-amber-300 bg-amber-500/15 ring-amber-500/30";
    default: return "text-rose-300 bg-rose-500/15 ring-rose-500/30";
  }
}

export function labelTheme(label: string): string {
  if (label.includes("EXCELLENT") || label.includes("ACCEPTABLE"))
    return "text-emerald-300 bg-emerald-500/15 ring-emerald-500/30";
  if (label.includes("DEGRADED")) return "text-amber-300 bg-amber-500/15 ring-amber-500/30";
  return "text-rose-300 bg-rose-500/15 ring-rose-500/30";
}

export function timeAgo(iso: string): string {
  const d = new Date(iso);
  const s = Math.floor((Date.now() - d.getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return d.toLocaleDateString();
}
