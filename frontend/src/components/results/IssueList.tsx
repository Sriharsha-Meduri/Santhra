import { AlertTriangle, CheckCircle2 } from "lucide-react";
import type { Issue } from "../../lib/types";
import { Badge, Meter } from "../atoms";
import { severityTheme, titleCase } from "../../lib/ui";

function IssueCard({ issue }: { issue: Issue }) {
  return (
    <div className="rounded-2xl border border-line bg-paper/70 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-ochre" />
          <span className="font-semibold text-ink">{titleCase(issue.type)}</span>
        </div>
        <Badge className={severityTheme(issue.severity)}>{issue.severity}</Badge>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
        <div>
          <div className="mb-1 flex justify-between text-muted">
            <span>AI model</span><span className="tabular-nums">{Math.round(issue.ml_probability * 100)}%</span>
          </div>
          <Meter value={issue.ml_probability} className="bg-clay" />
        </div>
        <div>
          <div className="mb-1 flex justify-between text-muted">
            <span>CV signal</span><span className="tabular-nums">{Math.round(issue.cv_severity * 100)}%</span>
          </div>
          <Meter value={issue.cv_severity} className="bg-forest" />
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
        <span>Confidence <b className="text-ink">{Math.round(issue.confidence * 100)}%</b></span>
        <span>Agreement <b className="text-ink">{Math.round(issue.agreement * 100)}%</b></span>
        {Object.entries(issue.evidence).map(([k, v]) => (
          <span key={k} className="rounded-md bg-paper-2 px-1.5 py-0.5 font-mono text-[11px] text-ink-soft">
            {k}={v}
          </span>
        ))}
      </div>
    </div>
  );
}

export function IssueList({ issues }: { issues: Issue[] }) {
  const detected = issues.filter((i) => i.detected).sort((a, b) => b.severity_value - a.severity_value);
  const clear = issues.filter((i) => !i.detected);
  return (
    <div className="space-y-3">
      {detected.length === 0 && (
        <div className="flex items-center gap-2 rounded-2xl border border-forest/20 bg-forest/[0.07] p-4 text-forest">
          <CheckCircle2 className="h-5 w-5" />
          <span className="font-medium">No quality issues detected.</span>
        </div>
      )}
      {detected.map((i) => <IssueCard key={i.type} issue={i} />)}
      {clear.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-1">
          {clear.map((i) => (
            <span key={i.type}
              className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs text-muted ring-1 ring-inset ring-line">
              <CheckCircle2 className="h-3 w-3 text-sage" /> {titleCase(i.type)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
