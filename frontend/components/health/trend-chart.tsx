"use client";

import { useState, useMemo } from "react";
import clsx from "clsx";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  CartesianGrid,
} from "recharts";
import { PeriodSelector } from "./period-selector";
import type { WeeklyTrend } from "@/lib/types";

const METRIC_COLORS: Record<string, string> = {
  rhr: "var(--color-accent-red)",
  hrv_sdnn: "var(--color-accent-green)",
  sleep_h: "var(--color-accent-purple)",
  vo2max: "var(--color-accent-blue)",
  weight_kg: "var(--color-accent-yellow)",
};

const LEFT_AXIS_METRICS = new Set(["rhr", "hrv_sdnn"]);

interface TrendChartProps {
  trends: WeeklyTrend[];
  weeks: number;
  onWeeksChange: (w: number) => void;
}

export function TrendChart({ trends, weeks, onWeeksChange }: TrendChartProps) {
  const [active, setActive] = useState<Set<string>>(
    () => new Set(["rhr", "hrv_sdnn"]),
  );

  const toggle = (m: string) => {
    setActive((prev) => {
      const next = new Set(prev);
      if (next.has(m)) next.delete(m);
      else next.add(m);
      return next;
    });
  };

  const chartData = useMemo(() => {
    const allWeeks = new Set<string>();
    for (const t of trends) for (const p of t.series) allWeeks.add(p.week);
    const weeks = [...allWeeks].sort();
    return weeks.map((w) => {
      const point: Record<string, string | number | null> = {
        week: w.replace(/^\d{4}-W/, "S"),
      };
      for (const t of trends) {
        const p = t.series.find((s) => s.week === w);
        point[t.metric] = p?.value ?? null;
      }
      return point;
    });
  }, [trends]);

  const hasRightAxis = trends.some(
    (t) => active.has(t.metric) && !LEFT_AXIS_METRICS.has(t.metric),
  );

  if (chartData.length === 0) {
    return (
      <div className="glass rounded-2xl p-5 text-center text-sm text-text-muted">
        Pas de données pour cette période
      </div>
    );
  }

  return (
    <div className="glass rounded-2xl p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-base font-semibold text-text-primary">Tendances</h3>
        <PeriodSelector value={weeks} onChange={onWeeksChange} />
      </div>
      <div className="mb-3 flex flex-wrap gap-1.5">
        {trends.map((t) => (
          <button
            key={t.metric}
            onClick={() => toggle(t.metric)}
            className={clsx(
              "rounded-lg px-2.5 py-1 text-xs font-medium transition-colors",
              active.has(t.metric)
                ? "bg-surface-2 text-text-primary"
                : "text-text-muted hover:bg-surface-1",
            )}
            style={
              active.has(t.metric)
                ? { borderLeft: `3px solid ${METRIC_COLORS[t.metric]}` }
                : undefined
            }
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="h-[200px] sm:h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="week"
              tick={{ fill: "var(--color-text-muted)", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              yAxisId="left"
              tick={{ fill: "var(--color-text-muted)", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={40}
            />
            {hasRightAxis && (
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={{ fill: "var(--color-text-muted)", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={40}
              />
            )}
            <Tooltip
              contentStyle={{
                background: "rgba(10,14,26,0.9)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 8,
                fontSize: 12,
              }}
              labelStyle={{ color: "var(--color-text-muted)" }}
            />
            {trends.map(
              (t) =>
                active.has(t.metric) && (
                  <Line
                    key={t.metric}
                    yAxisId={LEFT_AXIS_METRICS.has(t.metric) ? "left" : hasRightAxis ? "right" : "left"}
                    type="monotone"
                    dataKey={t.metric}
                    name={t.label}
                    stroke={METRIC_COLORS[t.metric]}
                    strokeWidth={2}
                    dot={false}
                    connectNulls
                    isAnimationActive={false}
                  />
                ),
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
