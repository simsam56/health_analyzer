"use client";

import { useState, useMemo, useCallback } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  TouchSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { toast } from "sonner";

import { useDashboard } from "@/lib/queries/use-dashboard";
import {
  usePlannerEvents,
  useBoardTasks,
  useCreateTask,
  useUpdateTask,
  useDeleteTask,
  useSyncCalendar,
  useCalendarStatus,
  useScheduleTask,
} from "@/lib/queries/use-planner";
import type { PlannerEvent, BoardTask, Category, TriageStatus } from "@/lib/types";

import { KpiBar } from "@/components/semaine/kpi-bar";
import { SyncStatus } from "@/components/semaine/sync-status";
import { WeekGrid } from "@/components/semaine/week-grid";
import { SidePanel } from "@/components/semaine/side-panel";
import { IdeasPanel } from "@/components/semaine/ideas-panel";
import { BacklogPanel } from "@/components/semaine/backlog-panel";
import { EventModal } from "@/components/semaine/event-modal";
import { EventPopover } from "@/components/semaine/event-popover";
import { DragOverlayContent } from "@/components/semaine/drag-overlay";
import { ChevronLeft, ChevronRight } from "lucide-react";

// ── Helpers ──────────────────────────────────────────────────────

function getMonday(d: Date): Date {
  const date = new Date(d);
  const day = date.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  date.setDate(date.getDate() + diff);
  date.setHours(0, 0, 0, 0);
  return date;
}

function addDays(d: Date, n: number): Date {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}

function toISO(d: Date): string {
  return d.toISOString().slice(0, 10) + "T00:00:00";
}

// ── Page ─────────────────────────────────────────────────────────

export default function SemainePage() {
  // ── Week navigation ──
  const [weekStart, setWeekStart] = useState(() => getMonday(new Date()));
  const weekEnd = useMemo(() => addDays(weekStart, 7), [weekStart]);

  // ── Data hooks ──
  const { data: dashboard, isLoading: dashLoading, error: dashError } = useDashboard();
  const { data: eventsData, isLoading: eventsLoading } = usePlannerEvents(
    toISO(weekStart),
    toISO(weekEnd)
  );
  const { data: boardData } = useBoardTasks();
  const { data: calStatus } = useCalendarStatus();

  const createTask = useCreateTask();
  const updateTask = useUpdateTask();
  const deleteTask = useDeleteTask();
  const syncCalendar = useSyncCalendar();
  const scheduleTask = useScheduleTask();

  const events = eventsData?.events ?? [];
  const boardTasks = boardData?.tasks ?? [];
  const ideas = useMemo(
    () => boardTasks.filter((t) => t.triage_status === "a_determiner"),
    [boardTasks]
  );

  // ── UI state ──
  const [sidePanelTab, setSidePanelTab] = useState<"ideas" | "backlog">("ideas");
  const [selectedEvent, setSelectedEvent] = useState<PlannerEvent | null>(null);
  const [showPopover, setShowPopover] = useState(false);
  const [modalMode, setModalMode] = useState<"create" | "edit" | null>(null);
  const [modalDefaults, setModalDefaults] = useState<{
    start: string;
    end: string;
  } | null>(null);

  // ── DnD ──
  const [dragItem, setDragItem] = useState<{
    type: "event" | "idea" | "backlog";
    event?: PlannerEvent;
    task?: BoardTask;
  } | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 200, tolerance: 5 } })
  );

  // ── Handlers ──

  const handleSlotClick = useCallback((date: Date, hour: number) => {
    const start = new Date(date);
    start.setHours(hour, 0, 0, 0);
    const end = new Date(start);
    end.setHours(hour + 1, 0, 0, 0);
    setModalDefaults({
      start: start.toISOString().slice(0, 16),
      end: end.toISOString().slice(0, 16),
    });
    setSelectedEvent(null);
    setModalMode("create");
  }, []);

  const handleEventClick = useCallback((event: PlannerEvent) => {
    setSelectedEvent(event);
    setShowPopover(true);
  }, []);

  const handleSaveEvent = useCallback(
    (data: {
      title: string;
      category: Category;
      start_at: string;
      end_at: string;
      notes: string;
      triage_status: TriageStatus;
    }) => {
      if (modalMode === "edit" && selectedEvent?.task_id) {
        updateTask.mutate(
          {
            id: selectedEvent.task_id,
            title: data.title,
            category: data.category,
            start_at: data.start_at,
            end_at: data.end_at,
            notes: data.notes,
            triage_status: data.triage_status,
            scheduled: true,
          },
          {
            onSuccess: () => {
              toast.success("Événement mis à jour");
              setModalMode(null);
            },
            onError: () => toast.error("Erreur lors de la mise à jour"),
          }
        );
      } else {
        createTask.mutate(
          {
            title: data.title,
            category: data.category,
            start_at: data.start_at,
            end_at: data.end_at,
            notes: data.notes,
            triage_status: data.triage_status,
            scheduled: true,
          },
          {
            onSuccess: () => {
              toast.success("Événement créé");
              setModalMode(null);
            },
            onError: () => toast.error("Erreur lors de la création"),
          }
        );
      }
    },
    [modalMode, selectedEvent, createTask, updateTask]
  );

  const handleDeleteEvent = useCallback(() => {
    if (!selectedEvent?.task_id) return;
    deleteTask.mutate(selectedEvent.task_id, {
      onSuccess: () => {
        toast.success("Événement supprimé");
        setSelectedEvent(null);
        setShowPopover(false);
        setModalMode(null);
      },
      onError: () => toast.error("Erreur lors de la suppression"),
    });
  }, [selectedEvent, deleteTask]);

  const handleCreateIdea = useCallback(
    (title: string, category: string) => {
      createTask.mutate(
        {
          title,
          category: "autre",
          triage_status: "a_determiner",
          notes: `Catégorie idée : ${category}`,
        },
        {
          onSuccess: () => toast.success("Idée ajoutée !"),
          onError: () => toast.error("Erreur lors de l'ajout"),
        }
      );
    },
    [createTask]
  );

  const handleSync = useCallback(() => {
    syncCalendar.mutate(undefined, {
      onSuccess: () => toast.success("Synchronisation terminée"),
      onError: () => toast.error("Erreur de synchronisation"),
    });
  }, [syncCalendar]);

  // ── Drag and drop ──

  const handleDragStart = useCallback((e: DragStartEvent) => {
    const data = e.active.data.current as
      | { type: "event"; event: PlannerEvent }
      | { type: "idea"; task: BoardTask }
      | { type: "backlog"; task: BoardTask }
      | undefined;
    if (!data) return;
    setDragItem(data);
  }, []);

  const handleDragEnd = useCallback(
    (e: DragEndEvent) => {
      setDragItem(null);
      const { active, over } = e;
      if (!over) return;

      const overId = String(over.id);
      // Parse slot ID: "slot:2026-03-14:09"
      const match = overId.match(/^slot:(\d{4}-\d{2}-\d{2}):(\d{2})$/);
      if (!match) return;

      const [, dateStr, hourStr] = match;
      const hour = parseInt(hourStr, 10);
      const startAt = `${dateStr}T${String(hour).padStart(2, "0")}:00:00`;
      const endHour = hour + 1;
      const endAt = `${dateStr}T${String(endHour).padStart(2, "0")}:00:00`;

      const data = active.data.current as
        | { type: "event"; event: PlannerEvent }
        | { type: "idea"; task: BoardTask }
        | { type: "backlog"; task: BoardTask }
        | undefined;

      if (!data) return;

      if (data.type === "event" && data.event.task_id) {
        // Move existing event
        const origStart = new Date(data.event.start_at);
        const origEnd = new Date(data.event.end_at);
        const durationMs = origEnd.getTime() - origStart.getTime();
        const newStart = new Date(`${startAt}`);
        const newEnd = new Date(newStart.getTime() + durationMs);

        updateTask.mutate(
          {
            id: data.event.task_id,
            start_at: newStart.toISOString(),
            end_at: newEnd.toISOString(),
            scheduled: true,
          },
          {
            onSuccess: () => toast.success("Événement déplacé"),
            onError: () => toast.error("Erreur lors du déplacement"),
          }
        );
      } else if (data.type === "idea" || data.type === "backlog") {
        // Schedule an idea or backlog task
        scheduleTask.mutate(
          {
            id: data.task.id,
            start_at: startAt,
            end_at: endAt,
          },
          {
            onSuccess: () =>
              toast.success(
                data.type === "idea"
                  ? "Idée planifiée !"
                  : "Tâche planifiée !"
              ),
            onError: () => toast.error("Erreur lors de la planification"),
          }
        );
      }
    },
    [updateTask, scheduleTask]
  );

  // ── Week navigation ──

  const weekLabel = useMemo(() => {
    const end = addDays(weekStart, 6);
    const opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" };
    return `${weekStart.toLocaleDateString("fr-FR", opts)} — ${end.toLocaleDateString("fr-FR", opts)}`;
  }, [weekStart]);

  // ── Loading / Error ──

  if (dashLoading && eventsLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent-blue border-t-transparent" />
      </div>
    );
  }

  if (dashError) {
    return (
      <div className="glass rounded-2xl p-6 text-center text-accent-red">
        Erreur de connexion à l&apos;API Python. Vérifiez que le serveur tourne
        sur le port 8765.
      </div>
    );
  }

  // ── Render ─────────────────────────────────────────────────────

  return (
    <DndContext
      sensors={sensors}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="flex h-[calc(100vh-120px)] flex-col gap-3">
        {/* Top bar: KPIs + week nav + sync */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <KpiBar
            readiness={dashboard?.readiness}
            summary={dashboard?.week?.summary}
          />
          <div className="flex items-center gap-2">
            <SyncStatus
              appleConnected={calStatus?.ok}
              applePermission={calStatus?.permission}
              appleError={calStatus?.error}
              isSyncing={syncCalendar.isPending}
              onSync={handleSync}
            />
          </div>
        </div>

        {/* Week navigation */}
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={() => setWeekStart((s) => addDays(s, -7))}
            className="rounded-lg p-1 text-text-muted hover:bg-surface-1 hover:text-text-primary"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <button
            onClick={() => setWeekStart(getMonday(new Date()))}
            className="rounded-lg px-3 py-1 text-xs font-medium text-text-secondary hover:bg-surface-1"
          >
            Aujourd&apos;hui
          </button>
          <span className="min-w-[160px] text-center text-sm font-medium text-text-primary">
            {weekLabel}
          </span>
          <button
            onClick={() => setWeekStart((s) => addDays(s, 7))}
            className="rounded-lg p-1 text-text-muted hover:bg-surface-1 hover:text-text-primary"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>

        {/* Main content: Grid + Side panel */}
        <div className="grid min-h-0 flex-1 grid-cols-[1fr_320px] gap-3">
          {/* Calendar grid */}
          <WeekGrid
            events={events}
            weekStart={weekStart}
            onSlotClick={handleSlotClick}
            onEventClick={handleEventClick}
          />

          {/* Side panel */}
          <SidePanel activeTab={sidePanelTab} onTabChange={setSidePanelTab}>
            {sidePanelTab === "ideas" ? (
              <IdeasPanel
                ideas={ideas}
                onCreateIdea={handleCreateIdea}
                isCreating={createTask.isPending}
              />
            ) : (
              <BacklogPanel tasks={boardTasks} />
            )}
          </SidePanel>
        </div>
      </div>

      {/* Drag overlay */}
      <DragOverlay dropAnimation={null}>
        {dragItem && (
          <DragOverlayContent
            type={dragItem.type}
            event={dragItem.event}
            task={dragItem.task}
          />
        )}
      </DragOverlay>

      {/* Event popover */}
      {showPopover && selectedEvent && (
        <EventPopover
          event={selectedEvent}
          onEdit={() => {
            setShowPopover(false);
            setModalMode("edit");
          }}
          onDelete={handleDeleteEvent}
          onClose={() => {
            setShowPopover(false);
            setSelectedEvent(null);
          }}
        />
      )}

      {/* Event modal (create / edit) */}
      {modalMode && (
        <EventModal
          event={modalMode === "edit" ? selectedEvent ?? undefined : undefined}
          defaultStart={modalDefaults?.start}
          defaultEnd={modalDefaults?.end}
          onSave={handleSaveEvent}
          onDelete={
            modalMode === "edit" ? handleDeleteEvent : undefined
          }
          onClose={() => {
            setModalMode(null);
            setSelectedEvent(null);
            setModalDefaults(null);
          }}
        />
      )}
    </DndContext>
  );
}
