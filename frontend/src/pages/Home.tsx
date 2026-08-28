import { useState } from "react";
import { AlertTriangle, Layers, RotateCcw, ScanSearch, Sparkles } from "lucide-react";
import { analyzeFile } from "../lib/api";
import type { AnalysisResult } from "../lib/types";
import { Uploader } from "../components/Uploader";
import { AnalysisPipeline } from "../components/AnalysisPipeline";
import { ResultView } from "../components/results/ResultView";

type Status = "idle" | "loading" | "done" | "error";

const FEATURES = [
  { kicker: "Hybrid", icon: Layers, t: "Two opinions, one verdict",
    d: "A learned CNN and a classical CV engine inspect every image, then a transparent fusion step reconciles them.",
    tone: "surface" },
  { kicker: "Honest", icon: ScanSearch, t: "Calibrated confidence",
    d: "Temperature-scaled class probabilities and a signal-agreement check, so uncertainty is shown, not hidden.",
    tone: "blush" },
  { kicker: "Explainable", icon: Sparkles, t: "See why, not just what",
    d: "Grad-CAM heatmaps, CV problem regions, forensics and a plain-language reason for every call.",
    tone: "forest" },
];

const STATS = [
  { n: "7", l: "Issue types" },
  { n: "CNN + AE + CV", l: "Signals fused" },
  { n: "0", l: "API keys" },
  { n: "Local", l: "Runs on CPU" },
];

function Features() {
  return (
    <section className="grid gap-4 sm:grid-cols-3">
      {FEATURES.map((f) => {
        const forest = f.tone === "forest";
        const blush = f.tone === "blush";
        return (
          <div key={f.t} className={cnTone(forest, blush)}>
            <f.icon className={forest ? "h-6 w-6 text-clay-soft" : "h-6 w-6 text-clay"} />
            <p className={`eyebrow mt-4 ${forest ? "!text-clay-soft" : ""}`}>{f.kicker}</p>
            <h3 className={`mt-1 font-display text-xl ${forest ? "text-paper" : "text-ink"}`}>{f.t}</h3>
            <p className={`mt-2 text-sm leading-relaxed ${forest ? "text-paper/75" : "text-muted"}`}>{f.d}</p>
          </div>
        );
      })}
    </section>
  );
}

function cnTone(forest: boolean, blush: boolean): string {
  const base = "rounded-[1.4rem] border p-6";
  if (forest) return `${base} border-forest bg-forest`;
  if (blush) return `${base} border-line bg-blush/60`;
  return `${base} border-line bg-surface`;
}

function Stats() {
  return (
    <section className="rounded-[1.4rem] border border-line bg-surface">
      <div className="grid grid-cols-2 divide-line sm:grid-cols-4 sm:divide-x">
        {STATS.map((s) => (
          <div key={s.l} className="px-6 py-6 text-center">
            <p className="font-display text-2xl text-ink sm:text-3xl">{s.n}</p>
            <p className="eyebrow mt-1 !text-muted">{s.l}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export function Home() {
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handle(file: File) {
    const url = URL.createObjectURL(file);
    setPreview(url);
    setStatus("loading");
    setError(null);
    setResult(null);
    try {
      const r = await analyzeFile(file);
      setResult(r);
      setStatus("done");
    } catch (e) {
      setError((e as Error).message);
      setStatus("error");
    }
  }

  function reset() {
    if (preview) URL.revokeObjectURL(preview);
    setPreview(null);
    setResult(null);
    setError(null);
    setStatus("idle");
  }

  return (
    <div className="space-y-12">
      {status === "idle" && (
        <>
          <section className="santhra-fade">
            <div className="max-w-3xl">
              <span className="eyebrow">Local image intelligence</span>
              <h1 className="mt-4 text-4xl leading-[1.05] text-ink sm:text-6xl">
                Know what is wrong with your image,{" "}
                <span className="highlight">before it ships.</span>
              </h1>
              <p className="mt-5 max-w-xl text-base leading-relaxed text-muted">
                Santhra inspects sharpness, exposure, noise, contrast, compression, colour and
                anomalies, then tells you not just <i>how bad</i>, but <i>what</i>, <i>where</i>,{" "}
                <i>how confident</i>, and <i>why</i>.
              </p>
            </div>
          </section>

          <Uploader onAnalyze={handle} />
          <Features />
          <Stats />
        </>
      )}

      {status === "loading" && <AnalysisPipeline preview={preview} />}

      {status === "error" && (
        <div className="santhra-fade rounded-[1.4rem] border border-danger/30 bg-danger/[0.06] p-8 text-center">
          <AlertTriangle className="mx-auto h-8 w-8 text-danger" />
          <p className="mt-3 font-display text-xl text-ink">Analysis failed</p>
          <p className="mt-1 text-sm text-muted">{error}</p>
          <button onClick={reset} className="btn btn-ink mt-5 px-5 py-2.5 text-sm">
            <RotateCcw className="h-4 w-4" /> Try again
          </button>
        </div>
      )}

      {status === "done" && result && (
        <div className="space-y-8">
          <div className="flex items-center justify-between">
            <div>
              <span className="eyebrow">Report</span>
              <h2 className="mt-1 font-display text-2xl text-ink">Analysis</h2>
            </div>
            <button onClick={reset} className="btn btn-outline px-4 py-2 text-sm">
              <RotateCcw className="h-4 w-4" /> New analysis
            </button>
          </div>
          <ResultView result={result} originalUrl={preview ?? undefined} />
        </div>
      )}
    </div>
  );
}
