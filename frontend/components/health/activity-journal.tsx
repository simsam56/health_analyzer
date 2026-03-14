"use client";

import { useMemo } from "react";
import {
  Footprints,
  Dumbbell,
  Bike,
  Waves,
  Mountain,
  PersonStanding,
  Timer,
} from "lucide-react";
import type { Activity } from "@/lib/types";
import type { LucideIcon } from "lucide-react";

const TYPE_ICONS: Record<string, LucideIcon> = {
  Running: Footprints,
  "Strength Training": Dumbbell,
  Cycling: Bike,
  Swimming: Waves,
  Hiking: Mountain,
  Walking: PersonStanding,
};

const TYPE_COLORS: Record<string, string> = {
  Running: "var(--color-sport)",
  "Strength Training": "var(--color-accent-blue)",
  Cycling: "var(--color-accent-yellow)",
  Swimming: "var(--color-accent-purple)",
  Hiking: "var(--color-formation)",
  Yoga: "var(--color-yoga)",
};

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("fr-FR", {
      weekday: "short",
      day: "numeric",
      month: "short",
    });
  } catch {
    return "";
  }
}

function formatDuration(s: number): string {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return h > 0 ? `${h}h${m.toString().padStart(2, "0")}` : `${m}min`;
}

interface ActivityJournalProps {
  activities: Activity[];
}

export function ActivityJournal({ activities }: ActivityJournalProps) {
  const groups = useMemo(() => {
    const map = new Map<string, { activities: Activity[]; totalS: number; totalKm: number }>();
    for (const a of activities) {
      const type = a.type || "Autre";
      if (!map.has(type)) map.set(type, { activities: [], totalS: 0, totalKm: 0 });
      const g = map.get(type)!;
      g.activities.push(a);
      g.totalS += a.duration_s || 0;
      g.totalKm += (a.distance_km ?? 0);
    }
    return [...map.entries()];
  }, [activities]);

  if (activities.length === 0) {
    return (
      <div className="glass rounded-2xl p-5 text-center text-sm text-text-muted">
        Aucune activité récente
      </div>
    );
  }

  return (
    <div className="glass rounded-2xl p-5">
      <h3 className="mb-3 flex items-center gap-2 text-base font-semibold text-text-primary">
        <Timer className="h-4 w-4 text-accent-blue" />
        Journal d&apos;activités
      </h3>
      <div className="space-y-4 max-h-[400px] overflow-y-auto">
        {groups.map(([type, group]) => {
          const Icon = TYPE_ICONS[type] ?? Timer;
          const color = TYPE_COLORS[type] ?? "var(--color-text-muted)";
          return (
            <div key={type}>
              <div className="mb-1.5 flex items-center gap-2">
                <Icon className="h-4 w-4" style={{ color }} />
                <span className="text-sm font-semibold text-text-primary">{type}</span>
                <span className="text-xs text-text-muted">
                  {formatDuration(group.totalS)}
                  {group.totalKm > 0 && ` · ${group.totalKm.toFixed(1)} km`}
                </span>
              </div>
              <div className="space-y-1">
                {group.activities.map((a) => (
                  <div
                    key={a.id}
                    className="flex items-center gap-2 rounded-lg bg-surface-0 px-3 py-1.5 text-sm"
                  >
                    <div className="flex-1">
                      <span className="text-text-primary">{a.name || type}</span>
                      <span className="ml-2 text-xs text-text-muted">
                        {formatDate(a.started_at)}
                      </span>
                    </div>
                    <span className="text-xs text-text-secondary">
                      {formatDuration(a.duration_s)}
                    </span>
                    {a.avg_hr && (
                      <span className="text-xs text-text-muted">{a.avg_hr} bpm</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
