import { useEffect, useRef, useState } from "react";
import { ImagePlus, Sparkles, UploadCloud, X } from "lucide-react";
import type { DemoSample } from "../lib/types";
import { fetchSampleBlob, loadDemoSamples } from "../lib/api";
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
    <div className="rounded-[1.4rem] border border-line bg-surface p-6 sm:p-7">
      {!file ? (
        <div
          role="button" tabIndex={0} aria-label="Upload an image: drop a file here or activate to browse"
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files?.[0]; if (f) stage(f); }}
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); inputRef.current?.click(); } }}
          className={cn(
            "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed px-6 py-16 text-center transition",
            dragging ? "border-clay bg-clay/[0.05]" : "border-line hover:border-clay/60 hover:bg-clay/[0.03]",
          )}>
          <div className="rounded-2xl bg-clay/12 p-4"><UploadCloud className="h-8 w-8 text-clay" /></div>
          <div>
            <p className="font-display text-xl text-ink">Drop an image, or click to browse</p>
            <p className="mt-1 eyebrow !text-muted">JPEG * PNG * BMP * WEBP * TIFF * up to {MAX_MB} MB</p>
          </div>
          <input ref={inputRef} type="file" accept={ACCEPT} hidden
            onChange={(e) => { const f = e.target.files?.[0]; if (f) stage(f); }} />
        </div>
      ) : (
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
          <div className="relative shrink-0">
            <img src={preview!} alt="preview" className="h-44 w-44 rounded-2xl object-cover ring-1 ring-line" />
            <button onClick={clear} aria-label="Remove"
              className="absolute -right-2 -top-2 rounded-full bg-ink p-1.5 text-white shadow hover:bg-black">
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="flex flex-1 flex-col justify-between gap-4">
            <div>
              <p className="font-display text-lg text-ink">{file.name}</p>
              <p className="mt-0.5 eyebrow !text-muted">{(file.size / 1024).toFixed(1)} KB * {file.type.replace("image/", "").toUpperCase()}</p>
            </div>
            <button onClick={() => onAnalyze(file)}
              className="btn btn-clay w-full px-5 py-3.5 text-base sm:w-auto">
              <Sparkles className="h-4 w-4" /> Analyze image
            </button>
          </div>
        </div>
      )}

      {error && <p className="mt-3 text-sm font-medium text-danger">{error}</p>}

      {samples.length > 0 && (
        <div className="mt-7 border-t border-line pt-5">
          <p className="mb-3 inline-flex items-center gap-1.5 eyebrow">
            <ImagePlus className="h-3.5 w-3.5" /> Try a sample
          </p>
          <div className="flex flex-wrap gap-2">
            {samples.map((s) => (
              <button key={s.key} onClick={() => pickSample(s)}
                className="rounded-full border border-line bg-paper px-3.5 py-1.5 text-sm font-medium text-ink-soft transition hover:border-clay hover:text-clay">
                {s.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
