import { cn, scoreTheme } from "../../lib/ui";

export function ScoreGauge({ score, size = 200 }: { score: number; size?: number }) {
  const theme = scoreTheme(score);
  const r = size / 2 - 14;
  const c = 2 * Math.PI * r;
  const dash = (score / 100) * c;
  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} className="stroke-slate-200 dark:stroke-white/10"
          strokeWidth={12} fill="none" />
        <circle cx={size / 2} cy={size / 2} r={r} className={cn(theme.ring, "transition-[stroke-dasharray] duration-700")}
          strokeWidth={12} fill="none" strokeLinecap="round" strokeDasharray={`${dash} ${c}`} />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className={cn("text-5xl font-bold tabular-nums", theme.text)}>{score}</span>
        <span className="text-xs font-medium text-slate-400 dark:text-slate-500">/ 100</span>
      </div>
    </div>
  );
}
