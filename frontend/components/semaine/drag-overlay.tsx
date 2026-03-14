"use client";

import type { PlannerEvent, BoardTask } from "@/lib/types";
import { CATEGORY_HEX } from "@/lib/constants";
import { Lightbulb, Calendar } from "lucide-react";

interface DragOverlayContentProps {
  type: "event" | "idea" | "backlog";
  event?: PlannerEvent;
  task?: BoardTask;
}

export function DragOverlayContent({
  type,
  event,
  task,
}: DragOverlayContentProps) {
  if (type === "event" && event) {
    const color = CATEGORY_HEX[event.category] ?? "#64748b";
    return (
      <div
        className="w-48 rounded-md border-l-[3px] px-2 py-1.5 shadow-lg"
        style={{
          borderLeftColor: color,
          background: `color-mix(in srgb, ${color} 15%, #0a0e1a)`,
        }}
      >
        <div className="flex items-center gap-1.5">
          <Calendar className="h-3 w-3 text-text-muted" />
          <span className="truncate text-xs font-medium text-text-primary">
            {event.title}
          </span>
        </div>
      </div>
    );
  }

  if (type === "idea" && task) {
    return (
      <div className="flex w-48 items-center gap-1.5 rounded-md bg-surface-1 px-2 py-1.5 shadow-lg">
        <Lightbulb className="h-3 w-3 text-accent-yellow" />
        <span className="truncate text-xs font-medium text-text-primary">
          {task.title}
        </span>
      </div>
    );
  }

  if (type === "backlog" && task) {
    const color = CATEGORY_HEX[task.category] ?? "#64748b";
    return (
      <div className="flex w-48 items-center gap-1.5 rounded-md bg-surface-1 px-2 py-1.5 shadow-lg">
        <div
          className="h-2 w-2 shrink-0 rounded-full"
          style={{ background: color }}
        />
        <span className="truncate text-xs font-medium text-text-primary">
          {task.title}
        </span>
      </div>
    );
  }

  return null;
}
