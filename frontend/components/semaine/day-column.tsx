"use client";

import type { PlannerEvent } from "@/lib/types";
import { GRID_START_HOUR, GRID_END_HOUR, HOUR_HEIGHT } from "@/lib/constants";
import { EventBlock } from "./event-block";
import { TimeIndicator } from "./time-indicator";
import { useDroppable } from "@dnd-kit/core";

interface DayColumnProps {
  date: Date;
  events: PlannerEvent[];
  isToday: boolean;
  hourHeight?: number;
  onSlotClick?: (date: Date, hour: number) => void;
  onEventClick?: (event: PlannerEvent) => void;
}

/** Compute overlap columns for events within a single day. */
function layoutEvents(events: PlannerEvent[]) {
  if (events.length === 0) return [];

  const sorted = [...events].sort(
    (a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime()
  );

  type Placed = { event: PlannerEvent; col: number; totalCols: number };
  const placed: Placed[] = [];
  const groups: Placed[][] = [];
  let currentGroup: Placed[] = [];
  let groupEnd = -Infinity;

  for (const event of sorted) {
    const start = new Date(event.start_at).getTime();
    const end = new Date(event.end_at).getTime();

    if (start >= groupEnd && currentGroup.length > 0) {
      groups.push(currentGroup);
      currentGroup = [];
      groupEnd = -Infinity;
    }

    // Find the first available column
    let col = 0;
    const occupiedCols = new Set(
      currentGroup
        .filter(
          (p) => new Date(p.event.end_at).getTime() > start
        )
        .map((p) => p.col)
    );
    while (occupiedCols.has(col)) col++;

    const item: Placed = { event, col, totalCols: 1 };
    currentGroup.push(item);
    groupEnd = Math.max(groupEnd, end);
  }
  if (currentGroup.length > 0) groups.push(currentGroup);

  // Set totalCols for each group
  for (const group of groups) {
    const maxCol = Math.max(...group.map((p) => p.col)) + 1;
    for (const item of group) {
      item.totalCols = maxCol;
      placed.push(item);
    }
  }

  return placed;
}

function HourSlot({
  date,
  hour,
  onSlotClick,
}: {
  date: Date;
  hour: number;
  onSlotClick?: (date: Date, hour: number) => void;
}) {
  const dateStr = date.toISOString().slice(0, 10);
  const slotId = `slot:${dateStr}:${String(hour).padStart(2, "0")}`;

  const { setNodeRef, isOver } = useDroppable({ id: slotId });

  return (
    <div
      ref={setNodeRef}
      className={`border-b border-white/[0.04] transition-colors ${
        isOver ? "bg-accent-blue/10" : ""
      }`}
      style={{ height: HOUR_HEIGHT }}
      onClick={() => onSlotClick?.(date, hour)}
    />
  );
}

export function DayColumn({
  date,
  events,
  isToday,
  hourHeight = HOUR_HEIGHT,
  onSlotClick,
  onEventClick,
}: DayColumnProps) {
  const hours = Array.from(
    { length: GRID_END_HOUR - GRID_START_HOUR },
    (_, i) => GRID_START_HOUR + i
  );

  const laidOut = layoutEvents(events);
  const totalHeight = (GRID_END_HOUR - GRID_START_HOUR) * hourHeight;

  return (
    <div
      className={`relative border-r border-white/[0.06] ${
        isToday ? "bg-accent-blue/[0.03]" : ""
      }`}
    >
      {/* Hour slots (droppable) */}
      <div style={{ height: totalHeight }}>
        {hours.map((h) => (
          <HourSlot key={h} date={date} hour={h} onSlotClick={onSlotClick} />
        ))}
      </div>

      {/* Event blocks */}
      {laidOut.map(({ event, col, totalCols }) => (
        <EventBlock
          key={event.id}
          event={event}
          hourHeight={hourHeight}
          columnIndex={col}
          totalColumns={totalCols}
          onClick={onEventClick}
        />
      ))}

      {/* Current time indicator */}
      {isToday && <TimeIndicator hourHeight={hourHeight} />}
    </div>
  );
}
