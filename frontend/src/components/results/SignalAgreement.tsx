import { Cpu, Radar, ScanLine } from "lucide-react";
import type { AnalysisResult } from "../../lib/types";
import { Badge, Meter } from "../atoms";
import { cn, titleCase } from "../../lib/ui";

export function SignalAgreement({ result }: { result: AnalysisResult }) {
  const detected = result.issues.filter((i) => i.detected);
  const ai = detected.length ? detected.reduce((s, i) => s + i.ml_probability, 0) / detected.length : 0;
  const cv = detected.length ? detected.reduce((s, i) => s + i.cv_severity, 0) / detected.length : 0;
  const anomaly = result.anomaly.score;
  const primary = result.explainability.primary_issue;
  const high = result.signal_agreement.overall === "HIGH_AGREEMENT";

  const rows = [
    { icon: Cpu, label: "AI Model", value: ai, tag: primary ? titleCase(primary) : "clear", color: "bg-brand-500" },
    { icon: ScanLine, label: "CV Analysis", value: cv, tag: primary ? titleCase(primary) : "clear", color: "bg-sky-400" },
    { icon: Radar, label: "Anomaly Model", value: anomaly, tag: `score ${anomaly.toFixed(2)}`, color: "bg-fuchsia-400" },
  ];

  return (
    <div className="space-y-3">
      {rows.map((r) => (
        <div key={r.label} className="flex items-center gap-3">
          <r.icon className="h-4 w-4 shrink-0 text-slate-400" />
          <span className="w-28 shrink-0 text-xs font-medium text-slate-500 dark:text-slate-400">{r.label}</span>
          <div className="flex-1"><Meter value={r.value} className={r.color} /></div>
          <span className="w-28 shrink-0 text-right text-[11px] text-slate-400">{r.tag}</span>
        </div>
      ))}
      <p className="text-[11px] leading-snug text-slate-400">
        Bars show relative signal strength. The anomaly value is a
        reconstruction-distance score (0 to 1) versus the clean-image reference,
        not a probability.
      </p>
      <div className="flex items-center justify-between pt-1">
        <span className="text-xs text-slate-400">Overall</span>
        <Badge className={cn(high
          ? "text-emerald-300 bg-emerald-500/15 ring-emerald-500/30"
          : "text-amber-300 bg-amber-500/15 ring-amber-500/30")}>
          {high ? "HIGH AGREEMENT" : "LOW AGREEMENT - REVIEW"}
        </Badge>
      </div>
    </div>
  );
}
