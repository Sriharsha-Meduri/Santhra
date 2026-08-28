import { cn, scoreTheme } from "../../lib/ui";

export function ScoreGauge({ score, size = 200 }: { score: number; size?: number }) {
  const theme = scoreTheme(score);
  const r = size / 2 - 14;
  const c = 2 * Math.PI * r;
  const dash = (score / 100) * c;
  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} className="stroke-sand"
          strokeWidth={12} fill="none" />
        <circle cx={size / 2} cy={size / 2} r={r} className={cn(theme.ring, "transition-[stroke-dasharray] duration-700")}
          strokeWidth={12} fill="none" strokeLinecap="round" strokeDasharray={`${dash} ${c}`} />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className={cn("font-display text-5xl font-semibold tabular-nums", theme.text)}>{score}</span>
        <span className="eyebrow !text-muted mt-0.5">/ 100</span>
      </div>
    </div>
  );
}
