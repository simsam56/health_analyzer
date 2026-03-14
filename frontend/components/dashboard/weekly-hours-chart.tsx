"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

interface WeeklyHoursChartProps {
  data: { week: string; hours: number }[];
}

export function WeeklyHoursChart({ data }: WeeklyHoursChartProps) {
  if (!data.length) return null;

  return (
    <div className="glass rounded-2xl p-5">
      <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-text-muted">
        Volume horaire hebdo
      </h3>
      <div className="h-40">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(255,255,255,0.04)"
              vertical={false}
            />
            <XAxis
              dataKey="week"
              tick={{ fontSize: 10, fill: "#64748b" }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v: string) => {
                const parts = v.split("-W");
                return parts[1] ? `S${parts[1]}` : v;
              }}
            />
            <YAxis
              tick={{ fontSize: 10, fill: "#64748b" }}
              tickLine={false}
              axisLine={false}
              unit="h"
            />
            <Tooltip
              contentStyle={{
                background: "rgba(10,14,26,0.95)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "8px",
                fontSize: "12px",
                color: "#f1f5f9",
              }}
              formatter={(value: number) => [`${value.toFixed(1)}h`, "Volume"]}
              labelFormatter={(v: string) => {
                const parts = v.split("-W");
                return parts[1] ? `Semaine ${parts[1]}` : v;
              }}
            />
            <Bar
              dataKey="hours"
              fill="#3b82f6"
              radius={[4, 4, 0, 0]}
              maxBarSize={32}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
