import type { AnalysisResult } from "../../lib/types";

export function Statistics({ result }: { result: AnalysisResult }) {
  const s = result.statistics;
  const rows: [string, string][] = [
    ["Resolution", `${result.image.width} × ${result.image.height}`],
    ["Aspect ratio", String(result.image.aspect_ratio)],
    ["Megapixels", String(result.image.megapixels)],
    ["File size", `${result.image.file_size_kb} KB`],
    ["Brightness", String(s.brightness)],
    ["Contrast (RMS)", String(s.contrast)],
    ["Sharpness (Lap.)", String(s.sharpness_laplacian)],
    ["Edge density", String(s.edge_density)],
    ["Noise σ", String(s.noise_sigma)],
    ["Saturation", String(s.saturation)],
    ["Highlight clip", `${s.highlight_clipping_pct}%`],
    ["Shadow clip", `${s.shadow_clipping_pct}%`],
    ["Blockiness", String(s.blockiness)],
    ["Entropy", String(s.entropy)],
  ];
  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-2.5 sm:grid-cols-3">
      {rows.map(([k, v]) => (
        <div key={k} className="flex items-baseline justify-between border-b border-dashed border-line pb-1.5">
          <span className="text-xs text-muted">{k}</span>
          <span className="font-mono text-xs font-medium text-ink">{v}</span>
        </div>
      ))}
    </div>
  );
}
