import { FlaskConical } from "lucide-react";
import type { ForensicCard } from "../../lib/types";
import { titleCase } from "../../lib/ui";

export function Forensics({ cards }: { cards: ForensicCard[] }) {
  if (!cards.length) {
    return <p className="text-sm text-muted">No forensic findings, the image passed all quality checks.</p>;
  }
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {cards.map((c) => (
        <div key={c.issue} className="rounded-2xl border border-line bg-paper/70 p-4">
          <div className="mb-2 flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-sm font-semibold text-ink">
              <FlaskConical className="h-4 w-4 text-clay" /> {c.signal}
            </span>
            <span className="text-xs font-semibold text-clay">{c.confidence}%</span>
          </div>
          <dl className="space-y-1.5 text-xs">
            <div><dt className="text-muted">Observed</dt>
              <dd className="font-mono text-[11px] text-ink">{c.observed}</dd></div>
            <div><dt className="text-muted">Model expectation</dt>
              <dd className="text-ink-soft">{c.model_expectation}</dd></div>
            <div><dt className="text-muted">Assessment</dt>
              <dd className="font-medium text-ink">{titleCase(c.assessment)}</dd></div>
          </dl>
        </div>
      ))}
    </div>
  );
}
