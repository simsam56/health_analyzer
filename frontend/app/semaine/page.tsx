"use client";

import { useCallback, useMemo, useState } from "react";
import { DndContext, DragOverlay, type DragEndEvent, type DragStartEvent } from "@dnd-kit/core";
import { useDashboard } from "@/lib/queries/use-dashboard";
import { usePlannerEvents, useBoardTasks, useUpdateTask } from "@/lib/queries/use-planner";
import { CATEGORY_COLORS } from "@/lib/constants";
import type { BoardTask, Category, PlannerEvent } from "@/lib/types";
import {
  getMonday,
  addWeeks,
  getDayColumns,
  groupEventsByDay,
  toISODate,
} from "@/lib/week-utils";
import { KpiBar } from "@/components/semaine/kpi-bar";
import { WeekNav } from "@/components/semaine/week-nav";
import { WeekGrid } from "@/components/semaine/week-grid";
import { SidePanel } from "@/components/semaine/side-panel";
import { EventModal } from "@/components/semaine/event-modal";

interface ModalState {
  mode: "create" | "edit";
  data: Partial<PlannerEvent> & { date?: string; hour?: number };
}

export default function SemainePage() {
  const [currentMonday, setCurrentMonday] = useState(() => getMonday(new Date()));
  const [sidePanelOpen, setSidePanelOpen] = useState(true);
  const [modalState, setModalState] = useState<ModalState | null>(null);
  const [draggingTask, setDraggingTask] = useState<BoardTask | null>(null);

  // Data
  const weekStart = toISODate(currentMonday) + "T00:00:00";
  const weekEndDate = addWeeks(currentMonday, 1);
  weekEndDate.setDate(weekEndDate.getDate() - 1);
  const weekEnd = toISODate(weekEndDate) + "T23:59:59";

  const { data: eventsData, isLoading: eventsLoading } = usePlannerEvents(weekStart, weekEnd);
  const { data: boardData } = useBoardTasks();
  const { data: dashData } = useDashboard();
  const updateTask = useUpdateTask();

  // Derived
  const days = useMemo(() => getDayColumns(currentMonday), [currentMonday]);
  const eventsByDay = useMemo(
    () => groupEventsByDay(eventsData?.events ?? [], currentMonday),
    [eventsData, currentMonday],
  );

  // DnD handlers
  const handleDragStart = useCallback((event: DragStartEvent) => {
    const task = event.active.data.current?.task as BoardTask | undefined;
    setDraggingTask(task ?? null);
  }, []);

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      setDraggingTask(null);
      const { active, over } = event;
      if (!over) return;
      const taskId = active.id as number;
      const dayIso = (over.id as string).replace("droppable-", "");
      const startAt = `${dayIso}T09:00:00`;
      const endAt = `${dayIso}T10:00:00`;
      updateTask.mutate({
        id: taskId,
        start_at: startAt,
        end_at: endAt,
        scheduled: true,
        scheduled_date: dayIso,
      });
    },
    [updateTask],
  );

  // Keyboard shortcuts
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (modalState) {
        if (e.key === "Escape") setModalState(null);
        return;
      }
      if (e.key === "ArrowLeft") setCurrentMonday((m) => addWeeks(m, -1));
      if (e.key === "ArrowRight") setCurrentMonday((m) => addWeeks(m, 1));
    },
    [modalState],
  );

  // Loading
  if (eventsLoading) {
    return (
      <div className="space-y-4">
        <div className="glass h-10 animate-pulse rounded-xl" />
        <div className="glass h-10 animate-pulse rounded-xl" />
        <div className="glass h-[60vh] animate-pulse rounded-xl" />
      </div>
    );
  }

  return (
    <div onKeyDown={handleKeyDown} tabIndex={-1} className="outline-none space-y-3">
      <KpiBar
        summary={dashData?.week?.summary}
        readiness={dashData?.readiness}
      />
      <WeekNav currentMonday={currentMonday} onChange={setCurrentMonday} />

      <DndContext onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
        <div className="flex gap-3">
          <div className="min-w-0 flex-1">
            <WeekGrid
              days={days}
              eventsByDay={eventsByDay}
              onSlotClick={(date, hour) =>
                setModalState({ mode: "create", data: { date, hour } })
              }
              onEventClick={(event) =>
                setModalState({ mode: "edit", data: event })
              }
            />
          </div>
          <SidePanel
            tasks={boardData?.tasks ?? []}
            isOpen={sidePanelOpen}
            onToggle={() => setSidePanelOpen((v) => !v)}
          />
        </div>

        <DragOverlay>
          {draggingTask && (
            <div
              className="rounded-lg bg-surface-2 px-3 py-2 text-xs font-medium text-text-primary shadow-lg"
              style={{
                borderLeft: `3px solid ${
                  CATEGORY_COLORS[draggingTask.category as Category] ??
                  "var(--color-autre)"
                }`,
              }}
            >
              {draggingTask.title}
            </div>
          )}
        </DragOverlay>
      </DndContext>

      {modalState && (
        <EventModal
          mode={modalState.mode}
          initialData={modalState.data}
          onClose={() => setModalState(null)}
        />
      )}
    </div>
  );
}
