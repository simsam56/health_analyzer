"use client";

import { useState, useEffect } from "react";
import type { PlannerEvent, Category, TriageStatus } from "@/lib/types";
import { CATEGORY_LABELS, CATEGORY_HEX, TRIAGE_LABELS } from "@/lib/constants";
import { X, Trash2 } from "lucide-react";

interface EventModalProps {
  event?: PlannerEvent;
  defaultStart?: string;
  defaultEnd?: string;
  onSave: (data: {
    title: string;
    category: Category;
    start_at: string;
    end_at: string;
    notes: string;
    triage_status: TriageStatus;
  }) => void;
  onDelete?: () => void;
  onClose: () => void;
}

const CATEGORIES = Object.keys(CATEGORY_LABELS) as Category[];
const TRIAGE_STATUSES: TriageStatus[] = [
  "a_planifier",
  "urgent",
  "non_urgent",
  "termine",
];

export function EventModal({
  event,
  defaultStart,
  defaultEnd,
  onSave,
  onDelete,
  onClose,
}: EventModalProps) {
  const isEdit = !!event;
  const [title, setTitle] = useState(event?.title ?? "");
  const [category, setCategory] = useState<Category>(event?.category ?? "autre");
  const [startAt, setStartAt] = useState(
    event?.start_at?.slice(0, 16) ?? defaultStart?.slice(0, 16) ?? ""
  );
  const [endAt, setEndAt] = useState(
    event?.end_at?.slice(0, 16) ?? defaultEnd?.slice(0, 16) ?? ""
  );
  const [notes, setNotes] = useState(event?.notes ?? "");
  const [triageStatus, setTriageStatus] = useState<TriageStatus>(
    event?.triage_status ?? "a_planifier"
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !startAt || !endAt) return;
    onSave({
      title: title.trim(),
      category,
      start_at: startAt.includes("T") ? startAt : `${startAt}:00`,
      end_at: endAt.includes("T") ? endAt : `${endAt}:00`,
      notes,
      triage_status: triageStatus,
    });
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="glass-strong w-full max-w-md rounded-2xl p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-base font-semibold text-text-primary">
            {isEdit ? "Modifier l\u2019\u00e9v\u00e9nement" : "Nouvel \u00e9v\u00e9nement"}
          </h3>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-text-muted hover:bg-surface-1 hover:text-text-primary"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          {/* Title */}
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Titre de l\u2019\u00e9v\u00e9nement..."
            className="w-full rounded-lg bg-surface-0 px-3 py-2 text-sm text-text-primary placeholder-text-muted outline-none focus:ring-1 focus:ring-accent-blue/50"
            autoFocus
          />

          {/* Category */}
          <div className="flex flex-wrap gap-1.5">
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setCategory(cat)}
                className={`rounded-md px-2 py-1 text-xs font-medium transition-colors ${
                  category === cat
                    ? "text-white"
                    : "bg-surface-0 text-text-muted hover:text-text-secondary"
                }`}
                style={
                  category === cat
                    ? { background: CATEGORY_HEX[cat] }
                    : undefined
                }
              >
                {CATEGORY_LABELS[cat]}
              </button>
            ))}
          </div>

          {/* Start / End */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="mb-1 block text-[10px] font-medium uppercase text-text-muted">
                D\u00e9but
              </label>
              <input
                type="datetime-local"
                value={startAt}
                onChange={(e) => setStartAt(e.target.value)}
                className="w-full rounded-lg bg-surface-0 px-2 py-1.5 text-xs text-text-primary outline-none focus:ring-1 focus:ring-accent-blue/50"
              />
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-medium uppercase text-text-muted">
                Fin
              </label>
              <input
                type="datetime-local"
                value={endAt}
                onChange={(e) => setEndAt(e.target.value)}
                className="w-full rounded-lg bg-surface-0 px-2 py-1.5 text-xs text-text-primary outline-none focus:ring-1 focus:ring-accent-blue/50"
              />
            </div>
          </div>

          {/* Triage status */}
          <div>
            <label className="mb-1 block text-[10px] font-medium uppercase text-text-muted">
              Statut
            </label>
            <select
              value={triageStatus}
              onChange={(e) => setTriageStatus(e.target.value as TriageStatus)}
              className="w-full rounded-lg bg-surface-0 px-2 py-1.5 text-xs text-text-primary outline-none"
            >
              {TRIAGE_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {TRIAGE_LABELS[s]}
                </option>
              ))}
            </select>
          </div>

          {/* Notes */}
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Notes..."
            rows={2}
            className="w-full rounded-lg bg-surface-0 px-3 py-2 text-sm text-text-primary placeholder-text-muted outline-none focus:ring-1 focus:ring-accent-blue/50"
          />

          {/* Actions */}
          <div className="flex items-center justify-between pt-1">
            {isEdit && onDelete ? (
              <button
                type="button"
                onClick={onDelete}
                className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium text-red-400 hover:bg-red-400/10"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Supprimer
              </button>
            ) : (
              <div />
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg px-3 py-1.5 text-xs font-medium text-text-muted hover:bg-surface-1"
              >
                Annuler
              </button>
              <button
                type="submit"
                disabled={!title.trim() || !startAt || !endAt}
                className="rounded-lg bg-accent-blue px-4 py-1.5 text-xs font-medium text-white hover:bg-accent-blue/90 disabled:opacity-40"
              >
                {isEdit ? "Enregistrer" : "Cr\u00e9er"}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
