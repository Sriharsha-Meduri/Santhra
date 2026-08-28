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
    { icon: Cpu, label: "AI Model", value: ai, tag: primary ? titleCase(primary) : "clear", color: "bg-clay" },
    { icon: ScanLine, label: "CV Analysis", value: cv, tag: primary ? titleCase(primary) : "clear", color: "bg-forest" },
    { icon: Radar, label: "Anomaly Model", value: anomaly, tag: `score ${anomaly.toFixed(2)}`, color: "bg-[#8a5a83]" },
  ];

  return (
    <div className="space-y-3">
      {rows.map((r) => (
        <div key={r.label} className="flex items-center gap-3">
          <r.icon className="h-4 w-4 shrink-0 text-muted" />
          <span className="w-28 shrink-0 text-xs font-medium text-muted">{r.label}</span>
          <div className="flex-1"><Meter value={r.value} className={r.color} /></div>
          <span className="w-28 shrink-0 text-right text-[11px] text-muted">{r.tag}</span>
        </div>
      ))}
      <p className="text-[11px] leading-snug text-muted">
        Bars show relative signal strength. The anomaly value is a
        reconstruction-distance score (0 to 1) versus the clean-image reference,
        not a probability.
      </p>
      <div className="flex items-center justify-between pt-1">
        <span className="text-xs text-muted">Overall</span>
        <Badge className={cn(high
          ? "text-forest bg-forest/10 ring-forest/25"
          : "text-ochre bg-ochre/12 ring-ochre/25")}>
          {high ? "High agreement" : "Low agreement, review"}
        </Badge>
      </div>
    </div>
  );
}
