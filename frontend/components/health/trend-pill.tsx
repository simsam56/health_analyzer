"use client";

import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import clsx from "clsx";
import {
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts";
import type { WeeklyTrend } from "@/lib/types";

interface TrendPillProps {
  trend: WeeklyTrend;
}

export function TrendPill({ trend }: TrendPillProps) {
  const TrendIcon =
    trend.trend === "up" ? TrendingUp : trend.trend === "down" ? TrendingDown : Minus;
  const color = trend.favorable ? "var(--color-accent-green)" : "var(--color-accent-red)";
  const isStable = trend.trend === "stable";

  return (
    <div className="glass rounded-xl p-3">
      <div className="text-xs text-text-muted">{trend.label}</div>
      <div className="mt-1 flex items-baseline gap-1">
        <span className="text-xl font-bold text-text-primary">
          {trend.current !== null ? trend.current : "—"}
        </span>
        {trend.unit && (
          <span className="text-xs text-text-muted">{trend.unit}</span>
        )}
      </div>
      {trend.delta !== null && (
        <div
          className={clsx(
            "mt-1 flex items-center gap-1 text-xs font-medium",
            isStable ? "text-text-muted" : trend.favorable ? "text-accent-green" : "text-accent-red",
          )}
        >
          <TrendIcon className="h-3 w-3" />
          <span>
            {trend.delta > 0 ? "+" : ""}
            {trend.delta} {trend.unit}
          </span>
        </div>
      )}
      {trend.series.length > 1 && (
        <div className="mt-2 h-6">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={trend.series}>
              <Line
                type="monotone"
                dataKey="value"
                stroke={isStable ? "var(--color-text-muted)" : color}
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
