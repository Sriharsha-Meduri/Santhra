import {
  PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer,
} from "recharts";
import { titleCase } from "../../lib/ui";

export function QualityRadar({ dimensions }: { dimensions: Record<string, number> }) {
  const data = Object.entries(dimensions).map(([k, v]) => ({ dim: titleCase(k), value: v }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <RadarChart data={data} outerRadius="72%">
        <PolarGrid stroke="currentColor" className="text-slate-300 dark:text-white/15" />
        <PolarAngleAxis dataKey="dim" tick={{ fontSize: 11, fill: "currentColor" }}
          className="text-slate-500 dark:text-slate-400" />
        {/* Fixed 0-100 domain so radars are comparable across images (recharts
            would otherwise auto-scale each chart to its own max). */}
        <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
        <Radar dataKey="value" stroke="#6366f1" fill="#6366f1" fillOpacity={0.35} />
      </RadarChart>
    </ResponsiveContainer>
  );
}
