"use client";

import type { LucideIcon } from "lucide-react";
import { clsx } from "clsx";

interface MetricCardProps {
  icon: LucideIcon;
  label: string;
  value: number | null | undefined;
  unit: string;
  daysOld?: number | null;
  freshness: number; // 0-1
  badge?: string;
}

export function MetricCard({
  icon: Icon,
  label,
  value,
  unit,
  daysOld,
  freshness,
  badge,
}: MetricCardProps) {
  const freshnessColor =
    freshness >= 0.8
      ? "text-accent-green"
      : freshness >= 0.5
        ? "text-accent-yellow"
        : "text-accent-red";

  const freshnessLabel =
    daysOld != null
      ? daysOld === 0
        ? "Auj."
        : daysOld === 1
          ? "Hier"
          : `J-${daysOld}`
      : null;

  return (
    <div className="glass rounded-xl p-3">
      <div className="flex items-center justify-between">
        <Icon className="h-3.5 w-3.5 text-text-muted" />
        {freshnessLabel && (
          <span className={clsx("text-[10px] font-medium", freshnessColor)}>
            {freshnessLabel}
          </span>
        )}
      </div>
      <div className="mt-2">
        <div className="text-xs text-text-muted">{label}</div>
        <div className="mt-0.5 flex items-baseline gap-1">
          <span className="text-xl font-bold text-text-primary">
            {value != null ? (typeof value === "number" ? value.toFixed(1) : value) : "—"}
          </span>
          {unit && <span className="text-xs text-text-muted">{unit}</span>}
        </div>
        {badge && (
          <span
            className={clsx(
              "mt-1 inline-block rounded px-1.5 py-0.5 text-[10px] font-medium uppercase",
              badge === "optimal"
                ? "bg-accent-green/20 text-accent-green"
                : badge === "surcharge"
                  ? "bg-accent-red/20 text-accent-red"
                  : "bg-accent-yellow/20 text-accent-yellow",
            )}
          >
            {badge}
          </span>
        )}
      </div>
      {/* Barre de fraîcheur */}
      <div className="mt-2 h-0.5 w-full rounded-full bg-surface-2">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${freshness * 100}%`,
            background:
              freshness >= 0.8
                ? "#22c55e"
                : freshness >= 0.5
                  ? "#ff9f0a"
                  : "#ff3b30",
          }}
        />
      </div>
    </div>
  );
}
