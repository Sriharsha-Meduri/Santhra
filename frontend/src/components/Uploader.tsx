import { useEffect, useRef, useState } from "react";
import { ImagePlus, Sparkles, UploadCloud, X } from "lucide-react";
import type { DemoSample } from "../lib/types";
import { fetchSampleBlob, loadDemoSamples } from "../lib/api";
import { Card } from "./atoms";
import { cn } from "../lib/ui";

const MAX_MB = 15;
const ACCEPT = "image/jpeg,image/png,image/bmp,image/webp,image/tiff";

export function Uploader({ onAnalyze }: { onAnalyze: (file: File) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [samples, setSamples] = useState<DemoSample[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { loadDemoSamples().then(setSamples); }, []);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  function stage(f: File) {
    setError(null);
    if (f.size > MAX_MB * 1024 * 1024) { setError(`File exceeds ${MAX_MB} MB.`); return; }
    if (!f.type.startsWith("image/")) { setError("Please choose an image file."); return; }
    setFile(f);
    setPreview(URL.createObjectURL(f));
  }

  async function pickSample(s: DemoSample) {
    try {
      const blob = await fetchSampleBlob(s.url);
      stage(new File([blob], `${s.key}.jpg`, { type: "image/jpeg" }));
    } catch {
      setError("Could not load the sample image.");
    }
  }

  function clear() { setFile(null); setPreview(null); setError(null); }

  return (
    <Card className="p-6">
      {!file ? (
        <div
          role="button" tabIndex={0} aria-label="Upload an image: drop a file here or activate to browse"
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files?.[0]; if (f) stage(f); }}
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); inputRef.current?.click(); } }}
          className={cn(
            "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed px-6 py-14 text-center transition",
            dragging
              ? "border-brand-500 bg-brand-500/10"
              : "border-slate-300 hover:border-brand-400 hover:bg-brand-500/[0.04] dark:border-white/15",
          )}>
          <div className="rounded-2xl bg-brand-500/15 p-4"><UploadCloud className="h-8 w-8 text-brand-400" /></div>
          <div>
            <p className="font-semibold">Drop an image, or click to browse</p>
            <p className="mt-1 text-xs text-slate-400">JPEG · PNG · BMP · WEBP · TIFF · up to {MAX_MB} MB</p>
          </div>
          <input ref={inputRef} type="file" accept={ACCEPT} hidden
            onChange={(e) => { const f = e.target.files?.[0]; if (f) stage(f); }} />
        </div>
      ) : (
        <div className="flex flex-col gap-4 sm:flex-row">
          <div className="relative">
            <img src={preview!} alt="preview" className="h-40 w-40 rounded-xl object-cover ring-1 ring-slate-200 dark:ring-white/10" />
            <button onClick={clear} className="absolute -right-2 -top-2 rounded-full bg-slate-800 p-1 text-white shadow hover:bg-slate-700">
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="flex flex-1 flex-col justify-between">
            <div className="text-sm">
              <p className="font-medium">{file.name}</p>
              <p className="text-xs text-slate-400">{(file.size / 1024).toFixed(1)} KB · {file.type}</p>
            </div>
            <button onClick={() => onAnalyze(file)}
              className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-brand-600 px-4 py-3 font-semibold text-white shadow-lg shadow-brand-600/25 transition hover:bg-brand-500 sm:w-auto">
              <Sparkles className="h-4 w-4" /> Analyze Image
            </button>
          </div>
        </div>
      )}

      {error && <p className="mt-3 text-sm text-rose-400">{error}</p>}

      {samples.length > 0 && (
        <div className="mt-6 border-t border-slate-200 pt-4 dark:border-white/10">
          <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            <ImagePlus className="h-3.5 w-3.5" /> Try a sample
          </p>
          <div className="flex flex-wrap gap-2">
            {samples.map((s) => (
              <button key={s.key} onClick={() => pickSample(s)}
                className="rounded-full border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-brand-400 hover:text-brand-500 dark:border-white/10 dark:text-slate-300 dark:hover:text-brand-300">
                {s.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
