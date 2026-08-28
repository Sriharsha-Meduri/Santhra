import { useEffect, useState } from "react";
import { Check, Loader2 } from "lucide-react";
import { cn } from "../lib/ui";

const STAGES = [
  "Uploading image",
  "Validating & decoding",
  "Extracting visual signals",
  "Running the AI model",
  "Cross-checking quality signals",
  "Generating explanation",
];

/** Indicative progress indicator. The labels mirror the real server-side
 *  pipeline stages, but their pacing is a fixed animation, NOT tied to backend
 *  events (the single /analyze request resolves independently and swaps this
 *  view out). The final stage stays "in progress" until the real response
 *  arrives, so no stage is ever shown complete after the request finishes. */
export function AnalysisPipeline({ preview }: { preview?: string | null }) {
  const [stage, setStage] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setStage((s) => Math.min(s + 1, STAGES.length - 1)), 550);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="santhra-fade rounded-[1.4rem] border border-line bg-surface p-7">
      <span className="eyebrow">Working</span>
      <div className="mt-4 flex flex-col gap-7 sm:flex-row sm:items-center">
        {preview && (
          <img src={preview} alt="analysing"
            className="h-36 w-36 rounded-2xl object-cover ring-1 ring-line" />
        )}
        <ol className="flex-1 space-y-3">
          {STAGES.map((label, i) => (
            <li key={label} className="flex items-center gap-3 text-sm">
              <span className={cn(
                "flex h-6 w-6 items-center justify-center rounded-full transition",
                i < stage ? "bg-forest/15 text-forest"
                  : i === stage ? "bg-clay/15 text-clay" : "bg-sand text-muted",
              )}>
                {i < stage ? <Check className="h-3.5 w-3.5" />
                  : i === stage ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <span className="text-[10px]">{i + 1}</span>}
              </span>
              <span className={cn(i <= stage ? "text-ink" : "text-muted")}>{label}</span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
