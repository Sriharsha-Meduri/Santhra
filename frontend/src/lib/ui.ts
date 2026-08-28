export function cn(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

export function titleCase(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Text / stroke / tint classes keyed to a 0-100 quality score. */
export function scoreTheme(score: number): { text: string; ring: string; bg: string; label: string } {
  if (score >= 90) return { text: "text-forest", ring: "stroke-forest", bg: "bg-forest/[0.06]", label: "Excellent" };
  if (score >= 75) return { text: "text-sage", ring: "stroke-sage", bg: "bg-sage/[0.08]", label: "Acceptable" };
  if (score >= 50) return { text: "text-ochre", ring: "stroke-ochre", bg: "bg-ochre/[0.08]", label: "Degraded" };
  return { text: "text-danger", ring: "stroke-danger", bg: "bg-danger/[0.06]", label: "Potentially defective" };
}

/** Pill badge classes (text + tint + ring) for a severity level. */
export function severityTheme(sev: string): string {
  switch (sev) {
    case "CRITICAL": return "text-danger bg-danger/10 ring-danger/25";
    case "HIGH": return "text-clay bg-clay/10 ring-clay/25";
    case "MEDIUM": return "text-ochre bg-ochre/12 ring-ochre/25";
    default: return "text-sage bg-sage/12 ring-sage/25";
  }
}

export function confidenceTheme(level: string): string {
  switch (level) {
    case "HIGH": return "text-forest bg-forest/10 ring-forest/25";
    case "MEDIUM": return "text-ochre bg-ochre/12 ring-ochre/25";
    default: return "text-danger bg-danger/10 ring-danger/25";
  }
}

export function labelTheme(label: string): string {
  if (label.includes("EXCELLENT") || label.includes("ACCEPTABLE"))
    return "text-forest bg-forest/10 ring-forest/25";
  if (label.includes("DEGRADED")) return "text-ochre bg-ochre/12 ring-ochre/25";
  return "text-danger bg-danger/10 ring-danger/25";
}

export function timeAgo(iso: string): string {
  const d = new Date(iso);
  const s = Math.floor((Date.now() - d.getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return d.toLocaleDateString();
}
