"use client";

import type { LucideIcon } from "lucide-react";
import { AreaChart, Area, ResponsiveContainer } from "recharts";

interface SparkMetricProps {
  icon: LucideIcon;
  label: string;
  value: number | null | undefined;
  unit: string;
  color: string;
  /** Optional series for sparkline (array of numbers) */
  spark?: number[];
  /** Freshness indicator: days since last measurement */
  daysOld?: number | null;
  /** Badge text (e.g. ACWR zone) */
  badge?: string;
}

export function SparkMetric({
  icon: Icon,
  label,
  value,
  unit,
  color,
  spark,
  daysOld,
  badge,
}: SparkMetricProps) {
  const sparkData = spark?.map((v, i) => ({ i, v }));

  const freshnessLabel =
    daysOld != null
      ? daysOld === 0
        ? "Auj."
        : daysOld === 1
          ? "Hier"
          : `J-${daysOld}`
      : null;

  const freshnessColor =
    daysOld != null
      ? daysOld <= 1
        ? "text-accent-green"
        : daysOld <= 3
          ? "text-accent-yellow"
          : "text-accent-red"
      : "";

  return (
    <div className="glass rounded-xl p-3 relative overflow-hidden">
      {/* Sparkline background */}
      {sparkData && sparkData.length > 1 && (
        <div className="absolute inset-0 opacity-20">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={sparkData} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={`spark-${label}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.4} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="v"
                stroke={color}
                strokeWidth={1.5}
                fill={`url(#spark-${label})`}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Content */}
      <div className="relative z-10">
        <div className="flex items-center justify-between">
          <Icon className="h-3.5 w-3.5 text-text-muted" />
          {freshnessLabel && (
            <span className={`text-[10px] font-medium ${freshnessColor}`}>
              {freshnessLabel}
            </span>
          )}
        </div>
        <div className="mt-2">
          <div className="text-[10px] font-medium uppercase tracking-wider text-text-muted">
            {label}
          </div>
          <div className="mt-0.5 flex items-baseline gap-1">
            <span className="text-xl font-bold tabular-nums" style={{ color }}>
              {value != null ? (typeof value === "number" ? value.toFixed(1) : value) : "\u2014"}
            </span>
            {unit && <span className="text-[10px] text-text-muted">{unit}</span>}
          </div>
          {badge && (
            <span
              className="mt-1 inline-block rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase"
              style={{
                background: `${color}20`,
                color,
              }}
            >
              {badge}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
