"use client";

import type { PlannerEvent } from "@/lib/types";
import { getCategoryColor } from "@/lib/utils";

interface EventTimelineProps {
  events: PlannerEvent[];
  limit?: number;
}

const DAY_NAMES = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"];

export function EventTimeline({ events, limit = 20 }: EventTimelineProps) {
  // Group events by day of week
  const grouped = new Map<number, PlannerEvent[]>();
  for (const e of events.slice(0, limit)) {
    const d = new Date(e.start_at);
    const day = (d.getDay() + 6) % 7; // Monday = 0
    if (!grouped.has(day)) grouped.set(day, []);
    grouped.get(day)!.push(e);
  }

  const today = new Date();
  const todayIdx = (today.getDay() + 6) % 7;

  return (
    <div className="glass rounded-2xl p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-text-muted">
          Cette semaine
        </h3>
        <span className="text-[10px] text-text-muted">
          {events.length} événements
        </span>
      </div>

      {events.length === 0 ? (
        <p className="text-sm text-text-muted">Aucun événement.</p>
      ) : (
        <div className="space-y-3">
          {DAY_NAMES.map((name, idx) => {
            const dayEvents = grouped.get(idx);
            if (!dayEvents) return null;
            const isToday = idx === todayIdx;

            return (
              <div key={idx} className="flex gap-3">
                {/* Day label */}
                <div className="w-8 shrink-0 pt-0.5 text-right">
                  <span
                    className={`text-[11px] font-semibold ${
                      isToday ? "text-accent-blue" : "text-text-muted"
                    }`}
                  >
                    {name}
                  </span>
                </div>

                {/* Timeline line */}
                <div className="relative flex w-3 flex-col items-center">
                  <div
                    className={`h-2.5 w-2.5 rounded-full border-2 ${
                      isToday
                        ? "border-accent-blue bg-accent-blue/30"
                        : "border-surface-3 bg-surface-1"
                    }`}
                  />
                  <div className="flex-1 w-px bg-surface-2" />
                </div>

                {/* Events */}
                <div className="flex-1 space-y-1 pb-2">
                  {dayEvents.map((e) => (
                    <div
                      key={e.id}
                      className="flex items-center gap-2 rounded-md bg-surface-0 px-2.5 py-1.5"
                    >
                      <div
                        className="h-1.5 w-1.5 rounded-full shrink-0"
                        style={{ background: getCategoryColor(e.category) }}
                      />
                      <span className="flex-1 text-xs">{e.title}</span>
                      <span className="text-[10px] tabular-nums text-text-muted">
                        {formatHour(e.start_at)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function formatHour(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}
