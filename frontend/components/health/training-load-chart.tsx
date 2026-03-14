"use client";

import { useMemo } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import type { WeeklyLoadBreakdown } from "@/lib/types";

const SPORT_COLORS: Record<string, string> = {
  Running: "var(--color-sport)",
  "Strength Training": "var(--color-accent-blue)",
  Cycling: "var(--color-accent-yellow)",
  Swimming: "var(--color-accent-purple)",
  Yoga: "var(--color-yoga)",
  Hiking: "var(--color-formation)",
  Walking: "var(--color-text-muted)",
  Golf: "var(--color-lecon)",
};

interface TrainingLoadChartProps {
  data: WeeklyLoadBreakdown[];
}

export function TrainingLoadChart({ data }: TrainingLoadChartProps) {
  const { chartData, sportTypes } = useMemo(() => {
    const types = new Set<string>();
    for (const w of data) {
      for (const t of Object.keys(w.breakdown)) types.add(t);
    }
    const chartData = data.map((w) => ({
      week: w.week.replace(/^\d{4}-W/, "S"),
      ...w.breakdown,
    }));
    return { chartData, sportTypes: [...types] };
  }, [data]);

  if (chartData.length === 0) {
    return (
      <div className="glass rounded-2xl p-5 text-center text-sm text-text-muted">
        Aucune activité enregistrée
      </div>
    );
  }

  return (
    <div className="glass rounded-2xl p-5">
      <h3 className="mb-4 text-base font-semibold text-text-primary">
        Charge d&apos;entraînement
      </h3>
      <div className="h-[200px] sm:h-[250px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="week"
              tick={{ fill: "var(--color-text-muted)", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "var(--color-text-muted)", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={30}
              label={{
                value: "heures",
                angle: -90,
                position: "insideLeft",
                style: { fill: "var(--color-text-muted)", fontSize: 10 },
              }}
            />
            <Tooltip
              contentStyle={{
                background: "rgba(10,14,26,0.9)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 8,
                fontSize: 12,
              }}
              labelStyle={{ color: "var(--color-text-muted)" }}
            />
            <Legend
              wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
            />
            {sportTypes.map((type) => (
              <Bar
                key={type}
                dataKey={type}
                stackId="a"
                fill={SPORT_COLORS[type] ?? "var(--color-text-muted)"}
                radius={[2, 2, 0, 0]}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
