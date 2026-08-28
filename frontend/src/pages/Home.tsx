import { useState } from "react";
import { AlertTriangle, Boxes, Gauge, RotateCcw, ScanSearch } from "lucide-react";
import { analyzeFile } from "../lib/api";
import type { AnalysisResult } from "../lib/types";
import { Uploader } from "../components/Uploader";
import { AnalysisPipeline } from "../components/AnalysisPipeline";
import { ResultView } from "../components/results/ResultView";

type Status = "idle" | "loading" | "done" | "error";

function Hero() {
  const feats = [
    { icon: ScanSearch, t: "Hybrid intelligence", d: "Learned CNN + classical CV, fused" },
    { icon: Gauge, t: "Calibrated confidence", d: "Temperature-scaled, honest uncertainty" },
    { icon: Boxes, t: "Explainable", d: "Grad-CAM, forensics & evidence" },
  ];
  return (
    <div className="santhra-fade text-center">
      <span className="inline-flex items-center gap-1.5 rounded-full border border-brand-500/30 bg-brand-500/10 px-3 py-1 text-xs font-medium text-brand-500 dark:text-brand-300">
        AI-Powered Image Quality & Defect Intelligence
      </span>
      <h1 className="mx-auto mt-4 max-w-2xl text-3xl font-bold tracking-tight sm:text-4xl">
        Know what's wrong with your image <span className="text-brand-500">before it reaches production.</span>
      </h1>
      <p className="mx-auto mt-3 max-w-xl text-sm text-slate-500 dark:text-slate-400">
        Santhra inspects sharpness, exposure, noise, contrast, compression, colour and anomalies -
        answering not just <i>how bad</i>, but <i>what</i>, <i>where</i>, <i>how confident</i> and <i>why</i>.
      </p>
      <div className="mx-auto mt-6 grid max-w-2xl grid-cols-1 gap-3 sm:grid-cols-3">
        {feats.map((f) => (
          <div key={f.t} className="rounded-xl border border-slate-200 bg-white/60 p-3 text-left dark:border-white/10 dark:bg-white/[0.03]">
            <f.icon className="h-5 w-5 text-brand-400" />
            <p className="mt-2 text-sm font-semibold">{f.t}</p>
            <p className="text-xs text-slate-400">{f.d}</p>
          </div>
        ))}
      </div>
    </div>
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
    <div className="space-y-8">
      {status === "idle" && <Hero />}
      {status === "idle" && <Uploader onAnalyze={handle} />}
      {status === "loading" && <AnalysisPipeline preview={preview} />}
      {status === "error" && (
        <div className="santhra-fade rounded-2xl border border-rose-500/30 bg-rose-500/10 p-6 text-center">
          <AlertTriangle className="mx-auto h-8 w-8 text-rose-400" />
          <p className="mt-2 font-semibold text-rose-500 dark:text-rose-300">Analysis failed</p>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{error}</p>
          <button onClick={reset} className="mt-4 inline-flex items-center gap-2 rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700">
            <RotateCcw className="h-4 w-4" /> Try again
          </button>
        </div>
      )}
      {status === "done" && result && (
        <>
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Analysis Report</h2>
            <button onClick={reset} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 dark:border-white/10 dark:text-slate-300 dark:hover:bg-white/10">
              <RotateCcw className="h-4 w-4" /> New analysis
            </button>
          </div>
          <ResultView result={result} originalUrl={preview ?? undefined} />
        </>
      )}
    </div>
  );
}
