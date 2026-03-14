"use client";

import clsx from "clsx";
import type { ACWRData } from "@/lib/types";

const ZONES = [
  { label: "Repos", min: 0, max: 0.5, color: "var(--color-text-muted)" },
  { label: "Léger", min: 0.5, max: 0.8, color: "var(--color-accent-blue)" },
  { label: "Optimal", min: 0.8, max: 1.3, color: "var(--color-accent-green)" },
  { label: "Élevé", min: 1.3, max: 1.5, color: "var(--color-accent-yellow)" },
  { label: "Danger", min: 1.5, max: 2.0, color: "var(--color-accent-red)" },
];

const GAUGE_MAX = 2.0;

interface ACWRGaugeProps {
  acwr: ACWRData | undefined;
}

export function ACWRGauge({ acwr }: ACWRGaugeProps) {
  if (!acwr) return null;

  const value = Math.min(acwr.acwr, GAUGE_MAX);
  const pct = (value / GAUGE_MAX) * 100;

  const currentZone = ZONES.find(
    (z) => acwr.acwr >= z.min && acwr.acwr < z.max,
  ) ?? ZONES[ZONES.length - 1];

  return (
    <div className="glass rounded-2xl p-4">
      <div className="mb-2 flex items-center justify-between">
        <h4 className="text-sm font-semibold text-text-primary">ACWR</h4>
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold text-text-primary">
            {acwr.acwr.toFixed(2)}
          </span>
          <span
            className={clsx(
              "rounded-md px-2 py-0.5 text-xs font-medium",
            )}
            style={{
              backgroundColor: `color-mix(in srgb, ${currentZone.color} 20%, transparent)`,
              color: currentZone.color,
            }}
          >
            {currentZone.label}
          </span>
        </div>
      </div>
      <div className="relative h-3 rounded-full overflow-hidden flex">
        {ZONES.map((z) => {
          const width = ((z.max - z.min) / GAUGE_MAX) * 100;
          return (
            <div
              key={z.label}
              className="h-full"
              style={{ width: `${width}%`, backgroundColor: z.color, opacity: 0.3 }}
            />
          );
        })}
        <div
          className="absolute top-1/2 h-5 w-1.5 -translate-y-1/2 rounded-full"
          style={{
            left: `${pct}%`,
            backgroundColor: currentZone.color,
            boxShadow: `0 0 6px ${currentZone.color}`,
          }}
        />
      </div>
      <div className="mt-2 flex justify-between text-[10px] text-text-muted">
        <span>0</span>
        <span>0.8</span>
        <span>1.3</span>
        <span>2.0</span>
      </div>
    </div>
  );
}
