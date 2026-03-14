"use client";

import { useEffect, useState } from "react";
import { useDroppable } from "@dnd-kit/core";
import { CATEGORY_COLORS } from "@/lib/constants";
import type { Category, PlannerEvent } from "@/lib/types";
import {
  HOURS,
  TOTAL_HOURS,
  eventTopAndHeight,
  formatHour,
  type DayColumn,
} from "@/lib/week-utils";

interface WeekGridProps {
  days: DayColumn[];
  eventsByDay: Map<string, PlannerEvent[]>;
  onSlotClick: (date: string, hour: number) => void;
  onEventClick: (event: PlannerEvent) => void;
}

const ROW_HEIGHT = 60; // px per hour
const GRID_HEIGHT = TOTAL_HOURS * ROW_HEIGHT;

export function WeekGrid({
  days,
  eventsByDay,
  onSlotClick,
  onEventClick,
}: WeekGridProps) {
  return (
    <div className="glass overflow-hidden rounded-xl">
      {/* Header row */}
      <div className="grid grid-cols-[56px_repeat(7,1fr)] border-b border-white/5">
        <div /> {/* gutter corner */}
        {days.map((day) => (
          <div
            key={day.iso}
            className={`px-2 py-2 text-center text-xs font-medium ${
              day.isToday
                ? "text-accent-blue"
                : "text-text-muted"
            }`}
          >
            <span className="capitalize">{day.label}</span>
            {day.isToday && (
              <div className="mx-auto mt-0.5 h-1 w-1 rounded-full bg-accent-blue" />
            )}
          </div>
        ))}
      </div>

      {/* Scrollable body */}
      <div
        className="overflow-y-auto"
        style={{ maxHeight: "calc(100vh - 240px)" }}
      >
        <div
          className="grid grid-cols-[56px_repeat(7,1fr)] relative"
          style={{ height: GRID_HEIGHT }}
        >
          {/* Hour labels in gutter */}
          {HOURS.map((h) => (
            <div
              key={`hour-${h}`}
              className="col-start-1 border-t border-white/5 pr-2 text-right text-[10px] text-text-muted"
              style={{
                position: "absolute",
                top: (h - HOURS[0]) * ROW_HEIGHT,
                left: 0,
                width: 56,
                height: ROW_HEIGHT,
                paddingTop: 2,
              }}
            >
              {formatHour(h)}
            </div>
          ))}

          {/* Day columns */}
          {days.map((day, colIdx) => (
            <DayColumnCell
              key={day.iso}
              day={day}
              colIdx={colIdx}
              events={eventsByDay.get(day.iso) ?? []}
              onSlotClick={onSlotClick}
              onEventClick={onEventClick}
            />
          ))}

          {/* Horizontal grid lines */}
          {HOURS.map((h) => (
            <div
              key={`line-${h}`}
              className="pointer-events-none col-span-full border-t border-white/5"
              style={{
                position: "absolute",
                top: (h - HOURS[0]) * ROW_HEIGHT,
                left: 56,
                right: 0,
                height: 0,
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Day Column (drop target) ──────────────────────────────────

function DayColumnCell({
  day,
  colIdx,
  events,
  onSlotClick,
  onEventClick,
}: {
  day: DayColumn;
  colIdx: number;
  events: PlannerEvent[];
  onSlotClick: (date: string, hour: number) => void;
  onEventClick: (event: PlannerEvent) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({
    id: `droppable-${day.iso}`,
  });

  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if ((e.target as HTMLElement).closest("[data-event]")) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const y = e.clientY - rect.top;
    const hour = Math.floor(y / ROW_HEIGHT) + HOURS[0];
    onSlotClick(day.iso, Math.min(Math.max(hour, HOURS[0]), HOURS[HOURS.length - 1]));
  };

  return (
    <div
      ref={setNodeRef}
      onClick={handleClick}
      className={`relative border-l border-white/5 cursor-pointer transition-colors ${
        isOver ? "bg-accent-blue/10" : ""
      }`}
      style={{
        gridColumn: colIdx + 2,
        gridRow: 1,
        height: GRID_HEIGHT,
      }}
    >
      {events.map((event) => (
        <EventBlock
          key={event.id}
          event={event}
          onClick={() => onEventClick(event)}
        />
      ))}
      {day.isToday && <NowIndicator />}
    </div>
  );
}

// ── Event Block ───────────────────────────────────────────────

function EventBlock({
  event,
  onClick,
}: {
  event: PlannerEvent;
  onClick: () => void;
}) {
  const { top, height } = eventTopAndHeight(event);
  const color = CATEGORY_COLORS[event.category as Category] ?? "var(--color-autre)";

  const startTime = new Date(event.start_at).toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div
      data-event
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      className="absolute left-0.5 right-0.5 cursor-pointer overflow-hidden rounded-md bg-surface-2 px-1.5 py-0.5 text-xs transition-all hover:brightness-125"
      style={{
        top,
        height,
        borderLeft: `3px solid ${color}`,
        minHeight: 20,
      }}
    >
      <div className="truncate font-medium text-text-primary">
        {event.title}
      </div>
      <div className="truncate text-[10px] text-text-muted">{startTime}</div>
    </div>
  );
}

// ── Now Indicator ─────────────────────────────────────────────

function NowIndicator() {
  const [top, setTop] = useState(calcNowTop());

  useEffect(() => {
    const id = setInterval(() => setTop(calcNowTop()), 60_000);
    return () => clearInterval(id);
  }, []);

  if (top < 0 || top > GRID_HEIGHT) return null;

  return (
    <div
      className="pointer-events-none absolute left-0 right-0 z-10"
      style={{ top }}
    >
      <div className="h-0.5 w-full bg-accent-red" />
      <div className="absolute -left-1 -top-1 h-2 w-2 rounded-full bg-accent-red" />
    </div>
  );
}

function calcNowTop(): number {
  const now = new Date();
  const minutes = (now.getHours() - HOURS[0]) * 60 + now.getMinutes();
  return (minutes / (TOTAL_HOURS * 60)) * GRID_HEIGHT;
}
