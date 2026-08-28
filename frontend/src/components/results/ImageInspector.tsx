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
      <div className="mb-3 inline-flex rounded-full border border-line bg-paper-2 p-1">
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)} disabled={!t.src}
            className={cn(
              "rounded-full px-3.5 py-1.5 text-xs font-semibold transition disabled:opacity-40",
              tab === t.key ? "bg-ink text-white shadow-sm" : "text-muted hover:text-ink",
            )}>{t.label}</button>
        ))}
      </div>
      <div className="overflow-hidden rounded-2xl border border-line bg-paper-2">
        {active.src
          ? <img src={active.src} alt={active.label} className="max-h-[420px] w-full object-contain" />
          : <div className="flex h-64 items-center justify-center text-sm text-muted">Not available</div>}
      </div>
      {active.caption && (
        <p className="mt-2 text-center eyebrow !text-muted">Method: {active.caption}</p>
      )}
    </div>
  );
}
