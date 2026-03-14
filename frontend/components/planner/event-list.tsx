"use client";

import type { PlannerEvent } from "@/lib/types";
import { getCategoryColor, formatTime } from "@/lib/utils";

interface EventListProps {
  events: PlannerEvent[];
  title?: string;
  limit?: number;
}

export function EventList({ events, title = "Cette semaine", limit = 15 }: EventListProps) {
  return (
    <section aria-label={title} data-section="evenements-semaine">
      <div className="glass rounded-2xl p-5">
        <h2 className="mb-4 text-lg font-semibold">
          {title}
          <span className="ml-2 text-sm font-normal text-text-muted">
            {events.length} événements
          </span>
        </h2>
        {events.length === 0 ? (
          <p className="text-text-muted">Aucun événement cette semaine.</p>
        ) : (
          <div className="space-y-2" role="list" aria-label="Événements">
            {events.slice(0, limit).map((e) => (
              <div
                key={e.id}
                role="listitem"
                data-event-id={e.id}
                data-event-category={e.category}
                className="flex items-center gap-3 rounded-lg bg-surface-0 px-3 py-2"
              >
                <div
                  className="h-2 w-2 rounded-full"
                  style={{ background: getCategoryColor(e.category) }}
                  aria-hidden="true"
                />
                <span className="flex-1 text-sm">{e.title}</span>
                <span className="text-xs text-text-muted">
                  {formatTime(e.start_at)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
