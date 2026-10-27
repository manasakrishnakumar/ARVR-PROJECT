import type { ReactNode } from "react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

/** Titled chart panel with an accessible text alternative. Colours come from CSS tokens so dark mode works. */
export function ChartCard({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return (
    <figure className="card chart">
      <figcaption><strong>{title}</strong><span className="muted"> {description}</span></figcaption>
      <div className="chart-box" role="img" aria-label={`${title}. ${description}`}>
        <ResponsiveContainer width="100%" height={220}>{children as React.ReactElement}</ResponsiveContainer>
      </div>
    </figure>
  );
}

const axis = { stroke: "var(--muted)", fontSize: 12 };
const grid = <CartesianGrid stroke="var(--grid)" strokeDasharray="3 3" />;
const tip = { contentStyle: { background: "var(--card)", border: "1px solid var(--grid)", color: "var(--text)" } };

export function TrendLines({ data, lines, domain, step }: {
  data: Record<string, number | string | null>[];
  lines: { key: string; name: string; color: string }[];
  domain?: [number | string, number | string];
  step?: boolean;
}) {
  return (
    <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
      {grid}
      <XAxis dataKey="n" {...axis} label={{ value: "session", position: "insideBottom", offset: -2, fill: "var(--muted)", fontSize: 11 }} />
      <YAxis {...axis} domain={domain ?? ["auto", "auto"]} allowDecimals={step ? false : true} />
      <Tooltip {...tip} />
      <Legend />
      {lines.map((l) => (
        <Line key={l.key} type={step ? "stepAfter" : "monotone"} dataKey={l.key} name={l.name} stroke={l.color}
              strokeWidth={2} dot={{ r: 3 }} connectNulls isAnimationActive={false} />
      ))}
    </LineChart>
  );
}

export function Bars({ data, bars, xKey }: {
  data: Record<string, number | string | null>[];
  bars: { key: string; name: string; color: string }[];
  xKey: string;
}) {
  return (
    <BarChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
      {grid}
      <XAxis dataKey={xKey} {...axis} />
      <YAxis {...axis} allowDecimals={false} />
      <Tooltip {...tip} />
      <Legend />
      {bars.map((b) => <Bar key={b.key} dataKey={b.key} name={b.name} fill={b.color} isAnimationActive={false} />)}
    </BarChart>
  );
}
