"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { BODY_FRONT_PATHS, BODY_BACK_PATHS } from "./muscle-map-paths";
import type { MusclePath } from "./muscle-map-paths";
import type { MuscleAlert } from "@/lib/types";
import { MuscleAlerts } from "./muscle-alerts";

interface MuscleMapProps {
  zones: Record<string, number>;
  weeklyVolume: Record<string, Record<string, unknown>>;
  alerts: MuscleAlert[];
}

function getMuscleColor(opacity: number): string {
  if (opacity > 0.7) return `rgba(239, 68, 68, ${opacity})`;   // red/intense
  if (opacity > 0.3) return `rgba(250, 204, 21, ${opacity})`;  // yellow/moderate
  return `rgba(148, 163, 184, ${Math.max(0.08, opacity)})`;     // gray/inactive
}

function BodySilhouette({
  paths,
  zones,
  label,
  onHover,
  hoveredMuscle,
}: {
  paths: MusclePath[];
  zones: Record<string, number>;
  label: string;
  onHover: (muscle: string | null, e?: React.MouseEvent) => void;
  hoveredMuscle: string | null;
}) {
  return (
    <div className="flex flex-col items-center gap-1">
      <span className="text-xs text-text-muted">{label}</span>
      <svg viewBox="0 0 120 280" className="h-52 w-auto sm:h-64">
        {paths.map((p) => {
          const opacity = p.muscle ? (zones[p.muscle] ?? 0.05) : 0;
          const isHovered = p.muscle && p.muscle === hoveredMuscle;
          return (
            <motion.path
              key={p.id}
              d={p.d}
              fill={p.muscle ? getMuscleColor(opacity) : "rgba(148,163,184,0.06)"}
              stroke="rgba(255,255,255,0.08)"
              strokeWidth={0.5}
              onMouseEnter={(e) => p.muscle && onHover(p.muscle, e)}
              onMouseLeave={() => onHover(null)}
              style={{ cursor: p.muscle ? "pointer" : "default" }}
              whileHover={p.muscle ? { scale: 1.03 } : undefined}
              animate={{ opacity: isHovered ? 1 : undefined }}
            />
          );
        })}
      </svg>
    </div>
  );
}

export default function MuscleMap({ zones, weeklyVolume, alerts }: MuscleMapProps) {
  const [hovered, setHovered] = useState<string | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  const handleHover = (muscle: string | null, e?: React.MouseEvent) => {
    setHovered(muscle);
    if (e && muscle) {
      const rect = (e.currentTarget as SVGElement).closest("div")?.getBoundingClientRect();
      if (rect) {
        setTooltipPos({ x: e.clientX - rect.left, y: e.clientY - rect.top - 40 });
      }
    }
  };

  // Get current week's volume for tooltip
  const currentWeekKey = Object.keys(weeklyVolume).sort().pop();
  const currentVol = currentWeekKey ? weeklyVolume[currentWeekKey] : {};

  return (
    <div className="glass rounded-2xl p-5">
      <h3 className="mb-4 text-base font-semibold text-text-primary">Carte musculaire</h3>
      <div className="relative flex flex-col items-center justify-center gap-6 sm:flex-row sm:gap-10">
        <BodySilhouette
          paths={BODY_FRONT_PATHS}
          zones={zones}
          label="Face"
          onHover={handleHover}
          hoveredMuscle={hovered}
        />
        <BodySilhouette
          paths={BODY_BACK_PATHS}
          zones={zones}
          label="Dos"
          onHover={handleHover}
          hoveredMuscle={hovered}
        />
        {hovered && (
          <div
            className="pointer-events-none absolute z-10 rounded-lg bg-bg/95 px-3 py-2 text-xs shadow-lg border border-surface-2"
            style={{ left: tooltipPos.x, top: tooltipPos.y }}
          >
            <div className="font-semibold text-text-primary">{hovered}</div>
            {currentVol[hovered] ? (
              <div className="text-text-muted">
                {(currentVol[hovered] as Record<string, number>).sets ?? 0} séries,{" "}
                {(currentVol[hovered] as Record<string, number>).sessions ?? 0} séances
              </div>
            ) : (
              <div className="text-text-muted">Aucune donnée</div>
            )}
          </div>
        )}
      </div>
      {alerts.length > 0 && <MuscleAlerts alerts={alerts} />}
    </div>
  );
}
