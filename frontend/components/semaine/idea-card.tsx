"use client";

import type { BoardTask } from "@/lib/types";
import { Lightbulb, GripVertical } from "lucide-react";
import { useDraggable } from "@dnd-kit/core";

interface IdeaCardProps {
  task: BoardTask;
}

function parseIdeaCategory(notes: string | null): string | null {
  if (!notes) return null;
  const match = notes.match(/Cat\u00e9gorie id\u00e9e\s*:\s*(.+)/i);
  return match ? match[1].trim() : null;
}

export function IdeaCard({ task }: IdeaCardProps) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `idea:${task.id}`,
    data: { type: "idea", task },
  });

  const ideaCategory = parseIdeaCategory(task.notes);

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
      <Lightbulb className="h-3 w-3 shrink-0 text-accent-yellow" />
      <span className="flex-1 truncate text-xs text-text-primary">
        {task.title}
      </span>
      {ideaCategory && (
        <span className="shrink-0 rounded bg-surface-2 px-1.5 py-0.5 text-[9px] font-medium text-text-muted">
          {ideaCategory}
        </span>
      )}
    </div>
  );
}
