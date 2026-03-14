"use client";

import { AlertTriangle, AlertCircle, CheckCircle } from "lucide-react";
import clsx from "clsx";
import type { MuscleAlert } from "@/lib/types";

const LEVEL_CONFIG: Record<string, { icon: typeof AlertTriangle; color: string }> = {
  critique: { icon: AlertTriangle, color: "text-accent-red" },
  faible: { icon: AlertCircle, color: "text-accent-yellow" },
  ok: { icon: CheckCircle, color: "text-text-muted" },
  optimal: { icon: CheckCircle, color: "text-accent-green" },
};

interface MuscleAlertsProps {
  alerts: MuscleAlert[];
}

export function MuscleAlerts({ alerts }: MuscleAlertsProps) {
  const relevant = alerts.filter(
    (a) => a.level === "critique" || a.level === "faible",
  );

  if (relevant.length === 0) return null;

  return (
    <div className="mt-4 space-y-1.5">
      {relevant.slice(0, 4).map((a, i) => {
        const cfg = LEVEL_CONFIG[a.level] ?? LEVEL_CONFIG.ok;
        const Icon = cfg.icon;
        return (
          <div key={i} className="flex items-center gap-2 text-xs">
            <Icon className={clsx("h-3.5 w-3.5 shrink-0", cfg.color)} />
            <span className="text-text-secondary">{a.message}</span>
          </div>
        );
      })}
    </div>
  );
}
