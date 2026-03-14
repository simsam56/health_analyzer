"use client";

import type { PlannerEvent } from "@/lib/types";
import { CATEGORY_HEX, GRID_START_HOUR, HOUR_HEIGHT } from "@/lib/constants";
import { SourceBadge } from "./source-badge";
import { AlertTriangle } from "lucide-react";
import { useDraggable } from "@dnd-kit/core";

interface EventBlockProps {
  event: PlannerEvent;
  hourHeight?: number;
  columnIndex: number;
  totalColumns: number;
  onClick?: (event: PlannerEvent) => void;
}

export function EventBlock({
  event,
  hourHeight = HOUR_HEIGHT,
  columnIndex,
  totalColumns,
  onClick,
}: EventBlockProps) {
  const start = new Date(event.start_at);
  const end = new Date(event.end_at);
  const startHours = start.getHours() + start.getMinutes() / 60;
  const endHours = end.getHours() + end.getMinutes() / 60;
  const durationHours = endHours - startHours;

  const top = (startHours - GRID_START_HOUR) * hourHeight;
  const height = Math.max(durationHours * hourHeight, 20);

  const color = CATEGORY_HEX[event.category] ?? "#64748b";
  const widthPercent = 100 / totalColumns;
  const leftPercent = columnIndex * widthPercent;

  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `event:${event.id}`,
    data: { type: "event", event },
    disabled: !event.editable,
  });

  const formatTime = (d: Date) =>
    d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      className={`absolute z-10 cursor-pointer overflow-hidden rounded-md border-l-[3px] transition-opacity ${
        isDragging ? "opacity-40" : "opacity-100"
      }`}
      style={{
        top,
        height,
        left: `${leftPercent}%`,
        width: `${widthPercent}%`,
        borderLeftColor: color,
        background: `${color}15`,
      }}
      onClick={(e) => {
        e.stopPropagation();
        onClick?.(event);
      }}
    >
      <div className="flex h-full flex-col px-1.5 py-1">
        <div className="flex items-start justify-between gap-1">
          <span className="truncate text-[11px] font-medium leading-tight text-text-primary">
            {event.title}
          </span>
          {event.conflict && (
            <AlertTriangle className="h-3 w-3 shrink-0 text-amber-400" />
          )}
        </div>
        <span className="text-[9px] text-text-muted">
          {formatTime(start)} – {formatTime(end)}
        </span>
        {height >= 50 && (
          <div className="mt-auto">
            <SourceBadge source={event.source} />
          </div>
        )}
      </div>
      {event.editable && (
        <div className="absolute bottom-0 left-0 right-0 h-1.5 cursor-s-resize hover:bg-white/10" />
      )}
    </div>
  );
}
