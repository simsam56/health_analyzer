"use client";

import type { BoardTask, TriageStatus } from "@/lib/types";
import { getCategoryColor } from "@/lib/utils";

interface BoardKanbanProps {
  tasks: BoardTask[];
  title?: string;
}

const TRIAGE_COLUMNS: { key: TriageStatus; label: string; dotColor: string }[] = [
  { key: "urgent", label: "Urgent", dotColor: "#ff3b30" },
  { key: "a_planifier", label: "À planifier", dotColor: "#ff9f0a" },
  { key: "non_urgent", label: "Non urgent", dotColor: "#64748b" },
  { key: "a_determiner", label: "À déterminer", dotColor: "#3b82f6" },
];

export function BoardKanban({ tasks, title = "Backlog" }: BoardKanbanProps) {
  const grouped = new Map<TriageStatus, BoardTask[]>();
  for (const t of tasks) {
    const status = t.triage_status ?? "a_determiner";
    if (!grouped.has(status)) grouped.set(status, []);
    grouped.get(status)!.push(t);
  }

  const visibleColumns = TRIAGE_COLUMNS.filter((col) => grouped.has(col.key));

  return (
    <section aria-label={title} data-section="board-backlog">
      <div className="glass rounded-2xl p-5">
        <h2 className="mb-4 text-lg font-semibold">
          {title}
          <span className="ml-2 text-sm font-normal text-text-muted">
            {tasks.length} tâches
          </span>
        </h2>
        {tasks.length === 0 ? (
          <p className="text-text-muted">Aucune tâche en backlog.</p>
        ) : (
          <div className="space-y-4">
            {visibleColumns.map(({ key, label, dotColor }) => (
              <div key={key} data-triage-group={key} role="group" aria-label={`Tâches ${label}`}>
                <div className="mb-2 flex items-center gap-2">
                  <div
                    className="h-2 w-2 rounded-full"
                    style={{ background: dotColor }}
                    aria-hidden="true"
                  />
                  <span className="text-xs font-semibold uppercase tracking-wide text-text-muted">
                    {label}
                  </span>
                  <span className="text-[10px] text-text-muted">
                    {grouped.get(key)!.length}
                  </span>
                </div>
                <div className="space-y-1.5" role="list" aria-label={`Liste tâches ${label}`}>
                  {grouped.get(key)!.map((t) => (
                    <div
                      key={t.id}
                      role="listitem"
                      data-task-id={t.id}
                      data-task-title={t.title}
                      data-task-category={t.category}
                      data-task-status={t.triage_status}
                      className="flex items-center gap-3 rounded-lg bg-surface-0 px-3 py-2"
                    >
                      <span
                        className="rounded px-1.5 py-0.5 text-[10px] font-medium uppercase"
                        style={{
                          background: `${getCategoryColor(t.category)}20`,
                          color: getCategoryColor(t.category),
                        }}
                      >
                        {t.category}
                      </span>
                      <span className="flex-1 text-sm">{t.title}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
