import { AlertOctagon, Clock, ShieldCheck, Sparkles } from "lucide-react";
import type { AnalysisResult } from "../../lib/types";
import { Badge, Card, SectionTitle } from "../atoms";
import { cn, confidenceTheme, labelTheme, scoreTheme, titleCase } from "../../lib/ui";
import { ScoreGauge } from "./ScoreGauge";
import { IssueList } from "./IssueList";
import { QualityRadar } from "./QualityRadar";
import { SignalAgreement } from "./SignalAgreement";
import { Forensics } from "./Forensics";
import { ImageInspector } from "./ImageInspector";
import { Statistics } from "./Statistics";

const ANOMALY_BADGE = "text-[#8a5a83] bg-[#8a5a83]/10 ring-[#8a5a83]/25";

export function ResultView({ result, originalUrl }: { result: AnalysisResult; originalUrl?: string }) {
  const theme = scoreTheme(result.quality_score);
  return (
    <div className="santhra-fade space-y-6">
      {/* Header / verdict */}
      <Card className="p-6 sm:p-7">
        <div className="flex flex-col items-center gap-7 sm:flex-row">
          <ScoreGauge score={result.quality_score} />
          <div className="flex-1 space-y-3 text-center sm:text-left">
            <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
              <Badge className={labelTheme(result.quality_label)}>{titleCase(result.quality_label)}</Badge>
              <Badge className={confidenceTheme(result.overall_confidence)}>
                <ShieldCheck className="h-3.5 w-3.5" /> {result.overall_confidence} confidence
              </Badge>
              {result.anomaly.detected && (
                <Badge className={ANOMALY_BADGE}>
                  <Sparkles className="h-3.5 w-3.5" /> Potential anomaly
                </Badge>
              )}
            </div>
            <p className="text-sm text-muted">
              <span className="font-medium text-ink">{result.filename}</span>
              {" · "}{result.image.width}×{result.image.height}{" · "}{result.format.toUpperCase()}
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3 text-xs text-muted sm:justify-start">
              <span className="inline-flex items-center gap-1"><Clock className="h-3.5 w-3.5" />
                {result.analysis_time_ms} ms</span>
              <span>Model score {result.model_info.model_score as number}</span>
              <span>CV score {result.model_info.cv_score as number}</span>
              {Object.entries(result.class_probabilities).map(([k, v]) => (
                <span key={k} className="rounded-md bg-paper-2 px-1.5 py-0.5">
                  {k.slice(0, 4)} {Math.round(v * 100)}%
                </span>
              ))}
            </div>
          </div>
        </div>
        {result.review_recommended && (
          <div className="mt-6 flex items-start gap-3 rounded-2xl border border-ochre/30 bg-ochre/[0.08] p-4 text-sm text-ink-soft">
            <AlertOctagon className="mt-0.5 h-5 w-5 shrink-0 text-ochre" />
            <div><b className="text-ink">Review recommended.</b> {result.review_reasons.join(" ")}</div>
          </div>
        )}
      </Card>

      {/* Image inspector + issues */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-5 sm:p-6">
          <SectionTitle title="Image Inspection" subtitle="Toggle AI heatmap & problem regions" />
          <ImageInspector original={originalUrl}
            heatmap={result.explainability.heatmap}
            problem={result.explainability.problem_regions}
            heatmapMethod={result.explainability.heatmap_method}
            problemMethod={result.explainability.problem_method} />
        </Card>
        <Card className="p-5 sm:p-6">
          <SectionTitle title="Detected Issues" subtitle="Fused AI + CV, per-issue severity" />
          <IssueList issues={result.issues} />
        </Card>
      </div>

      {/* Radar + signal agreement */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-5 sm:p-6">
          <SectionTitle title="Quality Breakdown" subtitle="Per-dimension score (measured)" />
          <QualityRadar dimensions={result.dimensions} />
        </Card>
        <Card className="p-5 sm:p-6">
          <SectionTitle title="Signal Agreement" subtitle="Do the independent detectors agree?" />
          <SignalAgreement result={result} />
        </Card>
      </div>

      {/* Forensics */}
      <Card className="p-5 sm:p-6">
        <SectionTitle title="Quality Forensics" subtitle="Observed signal vs learned expectation" />
        <Forensics cards={result.explainability.forensics} />
      </Card>

      {/* Narrative */}
      <Card className={cn("p-6", theme.bg)}>
        <SectionTitle title="Why did Santhra say this?" />
        <p className="text-[15px] leading-relaxed text-ink-soft">
          {result.explainability.narrative}
        </p>
        {result.explainability.evidence_cards.length > 0 && (
          <ul className="mt-4 space-y-2">
            {result.explainability.evidence_cards.map((e) => (
              <li key={e.issue} className="rounded-xl border border-line bg-surface p-3 text-sm">
                <div className="flex items-center justify-between">
                  <b className="text-ink">{titleCase(e.issue)} · {e.severity}</b>
                  <span className="text-xs text-muted">{e.confidence}%</span>
                </div>
                <p className="mt-1 text-ink-soft">{e.explanation}</p>
                <p className="mt-1 font-mono text-[11px] text-muted">{e.statistic}</p>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {/* Statistics */}
      <Card className="p-5 sm:p-6">
        <SectionTitle title="Image Statistics" subtitle="Interpretable CV measurements" />
        <Statistics result={result} />
      </Card>

      <p className="text-center eyebrow !text-muted">
        {String(result.model_info.model_name)} v{String(result.model_info.model_version)} *
        pipeline v{String((result.model_info as any).pipeline_version ?? "1.0.0")} *
        device {String(result.model_info.device)}
      </p>
    </div>
  );
}
