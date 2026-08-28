import { AlertTriangle, CheckCircle2 } from "lucide-react";
import type { Issue } from "../../lib/types";
import { Badge, Meter } from "../atoms";
import { cn, severityTheme, titleCase } from "../../lib/ui";

function IssueCard({ issue }: { issue: Issue }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-4 dark:border-white/10 dark:bg-white/[0.02]">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          <span className="font-semibold">{titleCase(issue.type)}</span>
        </div>
        <Badge className={severityTheme(issue.severity)}>{issue.severity}</Badge>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
        <div>
          <div className="mb-1 flex justify-between text-slate-500 dark:text-slate-400">
            <span>AI model</span><span className="tabular-nums">{Math.round(issue.ml_probability * 100)}%</span>
          </div>
          <Meter value={issue.ml_probability} className="bg-brand-500" />
        </div>
        <div>
          <div className="mb-1 flex justify-between text-slate-500 dark:text-slate-400">
            <span>CV signal</span><span className="tabular-nums">{Math.round(issue.cv_severity * 100)}%</span>
          </div>
          <Meter value={issue.cv_severity} className="bg-sky-400" />
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
        <span>Confidence <b className="text-slate-700 dark:text-slate-200">{Math.round(issue.confidence * 100)}%</b></span>
        <span>Agreement <b className="text-slate-700 dark:text-slate-200">{Math.round(issue.agreement * 100)}%</b></span>
        {Object.entries(issue.evidence).map(([k, v]) => (
          <span key={k} className="rounded bg-slate-200/60 px-1.5 py-0.5 font-mono text-[11px] dark:bg-white/5">
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
        <div className="flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-emerald-600 dark:text-emerald-300">
          <CheckCircle2 className="h-5 w-5" />
          <span className="font-medium">No quality issues detected.</span>
        </div>
      )}
      {detected.map((i) => <IssueCard key={i.type} issue={i} />)}
      {clear.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-1">
          {clear.map((i) => (
            <span key={i.type} className={cn(
              "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs",
              "text-slate-400 ring-1 ring-inset ring-slate-200 dark:text-slate-500 dark:ring-white/10",
            )}>
              <CheckCircle2 className="h-3 w-3" /> {titleCase(i.type)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
