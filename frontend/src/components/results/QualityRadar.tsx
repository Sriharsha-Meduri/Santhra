import {
  PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer,
} from "recharts";
import { titleCase } from "../../lib/ui";

export function QualityRadar({ dimensions }: { dimensions: Record<string, number> }) {
  const data = Object.entries(dimensions).map(([k, v]) => ({ dim: titleCase(k), value: v }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <RadarChart data={data} outerRadius="72%">
        <PolarGrid stroke="#e0d8c6" />
        <PolarAngleAxis dataKey="dim" tick={{ fontSize: 11, fill: "#79705f" }} />
        {/* Fixed 0-100 domain so radars are comparable across images (recharts
            would otherwise auto-scale each chart to its own max). */}
        <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
        <Radar dataKey="value" stroke="#c15a2f" fill="#c15a2f" fillOpacity={0.28} />
      </RadarChart>
    </ResponsiveContainer>
  );
}
