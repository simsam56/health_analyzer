"use client";

import type { PlannerEvent } from "@/lib/types";
import { GRID_START_HOUR, GRID_END_HOUR, HOUR_HEIGHT } from "@/lib/constants";
import { DayHeader } from "./day-header";
import { DayColumn } from "./day-column";
import { useMemo, useRef, useEffect } from "react";

interface WeekGridProps {
  events: PlannerEvent[];
  weekStart: Date;
  onSlotClick?: (date: Date, hour: number) => void;
  onEventClick?: (event: PlannerEvent) => void;
}

function getWeekDays(start: Date): Date[] {
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    return d;
  });
}

function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

export function WeekGrid({
  events,
  weekStart,
  onSlotClick,
  onEventClick,
}: WeekGridProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const days = useMemo(() => getWeekDays(weekStart), [weekStart]);
  const today = useMemo(() => new Date(), []);

  const hours = Array.from(
    { length: GRID_END_HOUR - GRID_START_HOUR },
    (_, i) => GRID_START_HOUR + i
  );

  // Group events by day
  const eventsByDay = useMemo(() => {
    const map = new Map<string, PlannerEvent[]>();
    for (const day of days) {
      map.set(day.toISOString().slice(0, 10), []);
    }
    for (const event of events) {
      const dateKey = event.start_at.slice(0, 10);
      const list = map.get(dateKey);
      if (list) list.push(event);
    }
    return map;
  }, [events, days]);

  // Auto-scroll to current hour on mount
  useEffect(() => {
    if (!scrollRef.current) return;
    const nowHour = new Date().getHours();
    const scrollTo = Math.max(0, (nowHour - GRID_START_HOUR - 1) * HOUR_HEIGHT);
    scrollRef.current.scrollTop = scrollTo;
  }, []);

  return (
    <div className="glass flex flex-col overflow-hidden rounded-2xl">
      {/* Day headers */}
      <div
        className="grid border-b border-white/[0.06]"
        style={{ gridTemplateColumns: `48px repeat(7, 1fr)` }}
      >
        <div /> {/* Time gutter spacer */}
        {days.map((day) => {
          const dateKey = day.toISOString().slice(0, 10);
          const count = eventsByDay.get(dateKey)?.length ?? 0;
          return (
            <DayHeader
              key={dateKey}
              date={day}
              isToday={isSameDay(day, today)}
              eventCount={count}
            />
          );
        })}
      </div>

      {/* Scrollable body */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div
          className="grid"
          style={{ gridTemplateColumns: `48px repeat(7, 1fr)` }}
        >
          {/* Time gutter */}
          <div className="relative">
            {hours.map((h) => (
              <div
                key={h}
                className="flex items-start justify-end border-b border-white/[0.04] pr-2 pt-0.5 text-[10px] font-medium text-text-muted"
                style={{ height: HOUR_HEIGHT }}
              >
                {String(h).padStart(2, "0")}:00
              </div>
            ))}
          </div>

          {/* Day columns */}
          {days.map((day) => {
            const dateKey = day.toISOString().slice(0, 10);
            const dayEvents = eventsByDay.get(dateKey) ?? [];
            return (
              <DayColumn
                key={dateKey}
                date={day}
                events={dayEvents}
                isToday={isSameDay(day, today)}
                onSlotClick={onSlotClick}
                onEventClick={onEventClick}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}
