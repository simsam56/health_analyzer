"use client";

import type { ReadinessData, WeekSummary } from "@/lib/types";

interface KpiBarProps {
  summary: WeekSummary | undefined;
  readiness: ReadinessData | undefined;
}

const chips = [
  { key: "readiness", label: "Readiness", field: null, unit: "/100", color: null },
  { key: "sport", label: "Sport", field: "sante_h" as const, unit: "h", color: "var(--color-sport)" },
  { key: "travail", label: "Travail", field: "travail_h" as const, unit: "h", color: "var(--color-travail)" },
  { key: "social", label: "Social", field: "relationnel_h" as const, unit: "h", color: "var(--color-social)" },
] as const;

export function KpiBar({ summary, readiness }: KpiBarProps) {
  return (
    <div className="glass flex items-center gap-4 rounded-xl px-4 py-2.5">
      {chips.map((chip) => {
        const value =
          chip.key === "readiness"
            ? readiness?.score ?? 0
            : summary?.[chip.field!] ?? 0;
        const color =
          chip.key === "readiness"
            ? readiness?.color ?? "#64748b"
            : chip.color;

        return (
          <div key={chip.key} className="flex items-baseline gap-1.5">
            <span className="text-xs text-text-muted">{chip.label}</span>
            <span className="text-lg font-bold" style={{ color: color ?? undefined }}>
              {value.toFixed(1)}
            </span>
            <span className="text-[10px] text-text-muted">{chip.unit}</span>
          </div>
        );
      })}
    </div>
  );
}
