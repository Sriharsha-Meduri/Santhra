import type { ReactNode } from "react";
import { cn } from "../lib/ui";

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn(
      "rounded-2xl border border-slate-200 bg-white shadow-sm",
      "dark:border-white/10 dark:bg-white/[0.035] dark:shadow-xl dark:shadow-black/30",
      className,
    )}>{children}</div>
  );
}

export function Badge({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span className={cn(
      "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset",
      className,
    )}>{children}</span>
  );
}

export function SectionTitle({ title, subtitle, right }: {
  title: string; subtitle?: string; right?: ReactNode;
}) {
  return (
    <div className="mb-4 flex items-end justify-between gap-3">
      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">{title}</h3>
        {subtitle && <p className="mt-0.5 text-xs text-slate-400 dark:text-slate-500">{subtitle}</p>}
      </div>
      {right}
    </div>
  );
}

export function Meter({ value, className }: { value: number; className?: string }) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-white/10">
      <div className={cn("h-full rounded-full transition-all", className)}
        style={{ width: `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%` }} />
    </div>
  );
}
