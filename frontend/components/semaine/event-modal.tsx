"use client";

import { useState } from "react";
import { X, Trash2 } from "lucide-react";
import { toast } from "sonner";
import {
  useCreateTask,
  useUpdateTask,
  useDeleteTask,
} from "@/lib/queries/use-planner";
import {
  CATEGORY_COLORS,
  CATEGORY_LABELS,
  CATEGORY_ICONS,
  TRIAGE_LABELS,
} from "@/lib/constants";
import type { Category, PlannerEvent, TriageStatus } from "@/lib/types";

interface ModalData {
  date?: string;
  hour?: number;
}

interface EventModalProps {
  mode: "create" | "edit";
  initialData: (Partial<PlannerEvent> & ModalData) | null;
  onClose: () => void;
}

const CATEGORIES = Object.keys(CATEGORY_LABELS) as Category[];
const TRIAGE_OPTIONS = Object.entries(TRIAGE_LABELS);

export function EventModal({ mode, initialData, onClose }: EventModalProps) {
  const create = useCreateTask();
  const update = useUpdateTask();
  const remove = useDeleteTask();

  const initDate =
    initialData?.date ?? initialData?.start_at?.slice(0, 10) ?? "";
  const initStartHour = initialData?.hour ?? (initialData?.start_at
    ? new Date(initialData.start_at).getHours()
    : 9);
  const initEndHour = initialData?.end_at
    ? new Date(initialData.end_at).getHours()
    : initStartHour + 1;

  const [title, setTitle] = useState(initialData?.title ?? "");
  const [category, setCategory] = useState<Category>(
    (initialData?.category as Category) ?? "autre",
  );
  const [date, setDate] = useState(initDate);
  const [startTime, setStartTime] = useState(
    initialData?.start_at
      ? initialData.start_at.slice(11, 16)
      : `${String(initStartHour).padStart(2, "0")}:00`,
  );
  const [endTime, setEndTime] = useState(
    initialData?.end_at
      ? initialData.end_at.slice(11, 16)
      : `${String(initEndHour).padStart(2, "0")}:00`,
  );
  const [notes, setNotes] = useState(initialData?.notes ?? "");
  const [triageStatus, setTriageStatus] = useState<TriageStatus>(
    initialData?.triage_status ?? "a_planifier",
  );
  const [confirmDelete, setConfirmDelete] = useState(false);

  const readOnly = mode === "edit" && initialData?.editable === false;
  const isPending = create.isPending || update.isPending || remove.isPending;

  const handleSave = () => {
    if (!title.trim() || !date) return;
    const startAt = `${date}T${startTime}:00`;
    const endAt = `${date}T${endTime}:00`;

    if (mode === "create") {
      create.mutate(
        {
          title: title.trim(),
          category,
          start_at: startAt,
          end_at: endAt,
          notes: notes || undefined,
          scheduled: true,
          triage_status: triageStatus,
        },
        {
          onSuccess: () => {
            toast.success("Événement créé");
            onClose();
          },
        },
      );
    } else {
      const taskId = initialData?.task_id ?? Number(initialData?.id);
      if (!taskId) return;
      update.mutate(
        {
          id: taskId,
          title: title.trim(),
          category,
          start_at: startAt,
          end_at: endAt,
          notes: notes || undefined,
          triage_status: triageStatus,
        },
        {
          onSuccess: () => {
            toast.success("Événement modifié");
            onClose();
          },
        },
      );
    }
  };

  const handleDelete = () => {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    const taskId = initialData?.task_id ?? Number(initialData?.id);
    if (!taskId) return;
    remove.mutate(taskId, {
      onSuccess: () => {
        toast.success("Événement supprimé");
        onClose();
      },
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal card */}
      <div className="glass-strong relative z-10 w-full max-w-md rounded-2xl p-6">
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-base font-semibold">
            {mode === "create" ? "Nouvel événement" : "Modifier"}
          </h3>
          <button
            onClick={onClose}
            className="rounded-lg p-1 hover:bg-surface-2 transition-colors"
          >
            <X className="h-4 w-4 text-text-muted" />
          </button>
        </div>

        {/* Title */}
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Titre..."
          readOnly={readOnly}
          className="mb-3 w-full rounded-lg bg-surface-0 px-3 py-2 text-sm text-text-primary placeholder-text-muted outline-none focus:ring-1 focus:ring-accent-blue/50"
        />

        {/* Category buttons */}
        <div className="mb-3 flex flex-wrap gap-1.5">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => !readOnly && setCategory(cat)}
              className={`rounded-lg px-2 py-1 text-xs font-medium transition-colors ${
                category === cat
                  ? "ring-1 ring-white/20"
                  : "opacity-50 hover:opacity-80"
              }`}
              style={{
                background: `color-mix(in srgb, ${CATEGORY_COLORS[cat]} 20%, transparent)`,
                color: CATEGORY_COLORS[cat],
              }}
            >
              {CATEGORY_ICONS[cat]} {CATEGORY_LABELS[cat]}
            </button>
          ))}
        </div>

        {/* Date + times */}
        <div className="mb-3 grid grid-cols-3 gap-2">
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            readOnly={readOnly}
            className="col-span-1 rounded-lg bg-surface-0 px-2 py-1.5 text-xs text-text-primary outline-none"
          />
          <input
            type="time"
            value={startTime}
            onChange={(e) => setStartTime(e.target.value)}
            readOnly={readOnly}
            className="rounded-lg bg-surface-0 px-2 py-1.5 text-xs text-text-primary outline-none"
          />
          <input
            type="time"
            value={endTime}
            onChange={(e) => setEndTime(e.target.value)}
            readOnly={readOnly}
            className="rounded-lg bg-surface-0 px-2 py-1.5 text-xs text-text-primary outline-none"
          />
        </div>

        {/* Triage status */}
        <select
          value={triageStatus}
          onChange={(e) => setTriageStatus(e.target.value as TriageStatus)}
          disabled={readOnly}
          className="mb-3 w-full rounded-lg bg-surface-0 px-2 py-1.5 text-xs text-text-secondary outline-none"
        >
          {TRIAGE_OPTIONS.map(([val, label]) => (
            <option key={val} value={val}>
              {label}
            </option>
          ))}
        </select>

        {/* Notes */}
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Notes..."
          readOnly={readOnly}
          rows={2}
          className="mb-4 w-full resize-none rounded-lg bg-surface-0 px-3 py-2 text-xs text-text-primary placeholder-text-muted outline-none focus:ring-1 focus:ring-accent-blue/50"
        />

        {/* Actions */}
        {!readOnly && (
          <div className="flex items-center justify-between">
            <div>
              {mode === "edit" && (
                <button
                  onClick={handleDelete}
                  disabled={isPending}
                  className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium text-accent-red hover:bg-accent-red/10 transition-colors disabled:opacity-50"
                >
                  <Trash2 className="h-3 w-3" />
                  {confirmDelete ? "Confirmer" : "Supprimer"}
                </button>
              )}
            </div>
            <div className="flex gap-2">
              <button
                onClick={onClose}
                className="rounded-lg px-3 py-1.5 text-xs text-text-muted hover:bg-surface-2 transition-colors"
              >
                Annuler
              </button>
              <button
                onClick={handleSave}
                disabled={isPending || !title.trim()}
                className="rounded-lg bg-accent-blue px-4 py-1.5 text-xs font-medium text-white hover:bg-accent-blue/80 transition-colors disabled:opacity-50"
              >
                {isPending ? "..." : "Enregistrer"}
              </button>
            </div>
          </div>
        )}

        {readOnly && (
          <p className="text-center text-[10px] text-text-muted">
            Événement Apple Calendar — lecture seule
          </p>
        )}
      </div>
    </div>
  );
}
