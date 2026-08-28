import { FlaskConical } from "lucide-react";
import type { ForensicCard } from "../../lib/types";
import { titleCase } from "../../lib/ui";

export function Forensics({ cards }: { cards: ForensicCard[] }) {
  if (!cards.length) {
    return <p className="text-sm text-slate-400">No forensic findings - the image passed all quality checks.</p>;
  }
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {cards.map((c) => (
        <div key={c.issue} className="rounded-xl border border-slate-200 bg-gradient-to-br from-slate-50 to-white p-4 dark:border-white/10 dark:from-white/[0.04] dark:to-transparent">
          <div className="mb-2 flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-sm font-semibold">
              <FlaskConical className="h-4 w-4 text-brand-400" /> {c.signal}
            </span>
            <span className="text-xs font-semibold text-brand-400">{c.confidence}%</span>
          </div>
          <dl className="space-y-1.5 text-xs">
            <div><dt className="text-slate-400">Observed</dt>
              <dd className="font-mono text-[11px] text-slate-700 dark:text-slate-200">{c.observed}</dd></div>
            <div><dt className="text-slate-400">Model expectation</dt>
              <dd className="text-slate-600 dark:text-slate-300">{c.model_expectation}</dd></div>
            <div><dt className="text-slate-400">Assessment</dt>
              <dd className="font-medium text-slate-800 dark:text-slate-100">{titleCase(c.assessment)}</dd></div>
          </dl>
        </div>
      ))}
    </div>
  );
}
