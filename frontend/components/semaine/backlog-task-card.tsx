"use client";

import type { BoardTask } from "@/lib/types";
import { CATEGORY_HEX } from "@/lib/constants";
import { GripVertical } from "lucide-react";
import { useDraggable } from "@dnd-kit/core";

interface BacklogTaskCardProps {
  task: BoardTask;
}

export function BacklogTaskCard({ task }: BacklogTaskCardProps) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `backlog:${task.id}`,
    data: { type: "backlog", task },
  });

  const color = CATEGORY_HEX[task.category] ?? "#64748b";

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      className={`flex cursor-grab items-center gap-2 rounded-lg bg-surface-0 px-2 py-1.5 transition-opacity active:cursor-grabbing ${
        isDragging ? "opacity-40" : "opacity-100"
      }`}
    >
      <GripVertical className="h-3 w-3 shrink-0 text-text-muted/50" />
      <div
        className="h-2 w-2 shrink-0 rounded-full"
        style={{ background: color }}
      />
      <span className="flex-1 truncate text-xs text-text-primary">
        {task.title}
      </span>
      <span
        className="shrink-0 rounded px-1 py-0.5 text-[8px] font-medium uppercase"
        style={{ background: `${color}15`, color }}
      >
        {task.category}
      </span>
    </div>
  );
}
