"use client";

import type { BoardTask } from "@/lib/types";
import { TRIAGE_LABELS } from "@/lib/constants";
import { BacklogTaskCard } from "./backlog-task-card";
import { ListTodo } from "lucide-react";

interface BacklogPanelProps {
  tasks: BoardTask[];
}

const BACKLOG_GROUPS: Array<{
  key: string;
  statuses: string[];
  label: string;
}> = [
  { key: "urgent", statuses: ["urgent"], label: "Urgent" },
  { key: "a_planifier", statuses: ["a_planifier"], label: "À planifier" },
  { key: "non_urgent", statuses: ["non_urgent"], label: "Non urgent" },
];

export function BacklogPanel({ tasks }: BacklogPanelProps) {
  // Filter out ideas (a_determiner) and completed (termine)
  const backlogTasks = tasks.filter(
    (t) => t.triage_status !== "a_determiner" && t.triage_status !== "termine"
  );

  if (backlogTasks.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-6 text-text-muted">
        <ListTodo className="h-5 w-5" />
        <p className="text-xs">Backlog vide. Bravo !</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {BACKLOG_GROUPS.map(({ key, statuses, label }) => {
        const groupTasks = backlogTasks.filter((t) =>
          statuses.includes(t.triage_status)
        );
        if (groupTasks.length === 0) return null;
        return (
          <div key={key}>
            <h4 className="mb-1 text-[10px] font-medium uppercase text-text-muted">
              {label} ({groupTasks.length})
            </h4>
            <div className="space-y-1">
              {groupTasks.map((task) => (
                <BacklogTaskCard key={task.id} task={task} />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
