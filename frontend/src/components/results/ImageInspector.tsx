import { useState } from "react";
import { cn } from "../../lib/ui";

type Tab = "original" | "heatmap" | "problem";

export function ImageInspector({ original, heatmap, problem, heatmapMethod, problemMethod }: {
  original?: string | null; heatmap?: string | null; problem?: string | null;
  heatmapMethod?: string; problemMethod?: string;
}) {
  const tabs: { key: Tab; label: string; src?: string | null; caption?: string }[] = [
    { key: "original", label: "Original", src: original },
    { key: "heatmap", label: "AI Heatmap", src: heatmap, caption: heatmapMethod },
    { key: "problem", label: "Problem Regions", src: problem, caption: problemMethod },
  ];
  const [tab, setTab] = useState<Tab>("original");
  const active = tabs.find((t) => t.key === tab)!;

  return (
    <div>
      <div className="mb-3 inline-flex rounded-lg border border-slate-200 bg-slate-100 p-0.5 dark:border-white/10 dark:bg-white/5">
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)} disabled={!t.src}
            className={cn(
              "rounded-md px-3 py-1.5 text-xs font-medium transition disabled:opacity-40",
              tab === t.key
                ? "bg-white text-slate-900 shadow-sm dark:bg-white/15 dark:text-white"
                : "text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white",
            )}>{t.label}</button>
        ))}
      </div>
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-slate-900/5 dark:border-white/10 dark:bg-black/30">
        {active.src
          ? <img src={active.src} alt={active.label} className="max-h-[420px] w-full object-contain" />
          : <div className="flex h-64 items-center justify-center text-sm text-slate-400">Not available</div>}
      </div>
      {active.caption && (
        <p className="mt-2 text-center text-[11px] text-slate-400">Method: {active.caption}</p>
      )}
    </div>
  );
}
