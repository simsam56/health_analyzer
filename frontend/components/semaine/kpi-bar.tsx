"use client";

import type { ReadinessData, WeekSummary } from "@/lib/types";

interface KpiBarProps {
  readiness?: ReadinessData;
  summary?: WeekSummary;
}

function MiniKpi({
  label,
  value,
  unit,
  color,
}: {
  label: string;
  value: number;
  unit: string;
  color: string;
}) {
  return (
    <div className="flex items-center gap-2 rounded-lg bg-surface-0 px-3 py-1.5">
      <span className="text-[10px] font-medium uppercase text-text-muted">
        {label}
      </span>
      <span className="text-sm font-bold" style={{ color }}>
        {typeof value === "number" ? value.toFixed(1) : value}
      </span>
      <span className="text-[10px] text-text-muted">{unit}</span>
    </div>
  );
}

export function KpiBar({ readiness, summary }: KpiBarProps) {
  return (
    <div className="flex items-center gap-2 overflow-x-auto">
      <MiniKpi
        label="Readiness"
        value={readiness?.score ?? 0}
        unit="/100"
        color={readiness?.color ?? "#64748b"}
      />
      <MiniKpi
        label="Sport"
        value={summary?.sante_h ?? 0}
        unit="h"
        color="var(--color-sport)"
      />
      <MiniKpi
        label="Travail"
        value={summary?.travail_h ?? 0}
        unit="h"
        color="var(--color-travail)"
      />
      <MiniKpi
        label="Social"
        value={summary?.relationnel_h ?? 0}
        unit="h"
        color="var(--color-social)"
      />
    </div>
  );
}
