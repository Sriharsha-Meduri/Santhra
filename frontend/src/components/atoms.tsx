import type { ReactNode } from "react";
import { cn } from "../lib/ui";

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn(
      "rounded-[1.4rem] border border-line bg-surface",
      "shadow-[0_1px_0_rgba(255,255,255,0.6)_inset,0_18px_40px_-30px_rgba(28,26,21,0.35)]",
      className,
    )}>{children}</div>
  );
}

export function Badge({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span className={cn(
      "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide ring-1 ring-inset",
      className,
    )}>{children}</span>
  );
}

export function Eyebrow({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cn("eyebrow", className)}>{children}</span>;
}

export function SectionTitle({ title, subtitle, right }: {
  title: string; subtitle?: string; right?: ReactNode;
}) {
  return (
    <div className="mb-4 flex items-end justify-between gap-3">
      <div>
        <h3 className="eyebrow">{title}</h3>
        {subtitle && <p className="mt-1 text-xs text-muted">{subtitle}</p>}
      </div>
      {right}
    </div>
  );
}

export function Meter({ value, className }: { value: number; className?: string }) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-sand">
      <div className={cn("h-full rounded-full transition-all duration-500", className)}
        style={{ width: `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%` }} />
    </div>
  );
}
