"use client";

import type { PlannerEvent } from "@/lib/types";
import { CATEGORY_LABELS, CATEGORY_HEX } from "@/lib/constants";
import { SourceBadge } from "./source-badge";
import { Pencil, Trash2, X, AlertTriangle } from "lucide-react";
import { useEffect } from "react";

interface EventPopoverProps {
  event: PlannerEvent;
  onEdit: () => void;
  onDelete: () => void;
  onClose: () => void;
}

export function EventPopover({
  event,
  onEdit,
  onDelete,
  onClose,
}: EventPopoverProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const start = new Date(event.start_at);
  const end = new Date(event.end_at);
  const color = CATEGORY_HEX[event.category] ?? "#64748b";

  const formatDateTime = (d: Date) =>
    d.toLocaleDateString("fr-FR", {
      weekday: "short",
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });

  return (
    <div className="fixed inset-0 z-50" onClick={onClose}>
      <div
        className="glass-strong absolute left-1/2 top-1/2 w-80 -translate-x-1/2 -translate-y-1/2 rounded-xl p-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="mb-3 flex items-start justify-between">
          <div className="flex items-center gap-2">
            <div
              className="h-3 w-3 rounded-full"
              style={{ background: color }}
            />
            <h4 className="text-sm font-semibold text-text-primary">
              {event.title}
            </h4>
          </div>
          <button
            onClick={onClose}
            className="rounded p-0.5 text-text-muted hover:text-text-primary"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>

        {/* Details */}
        <div className="space-y-2 text-xs text-text-secondary">
          <div>
            {formatDateTime(start)} — {formatDateTime(end)}
          </div>
          <div className="flex items-center gap-2">
            <span
              className="rounded px-1.5 py-0.5 text-[10px] font-medium"
              style={{ background: `${color}20`, color }}
            >
              {CATEGORY_LABELS[event.category]}
            </span>
            <SourceBadge source={event.source} />
          </div>
          {event.conflict && (
            <div className="flex items-center gap-1.5 rounded-lg bg-amber-400/10 px-2 py-1.5 text-amber-400">
              <AlertTriangle className="h-3.5 w-3.5" />
              <span>Conflit d\u00e9tect\u00e9 avec le calendrier externe</span>
            </div>
          )}
          {event.notes && (
            <p className="text-text-muted">{event.notes}</p>
          )}
        </div>

        {/* Actions */}
        {event.editable && (
          <div className="mt-3 flex justify-end gap-2 border-t border-white/[0.06] pt-3">
            <button
              onClick={onDelete}
              className="flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-red-400 hover:bg-red-400/10"
            >
              <Trash2 className="h-3 w-3" />
              Supprimer
            </button>
            <button
              onClick={onEdit}
              className="flex items-center gap-1 rounded-lg bg-accent-blue/20 px-3 py-1 text-xs font-medium text-accent-blue hover:bg-accent-blue/30"
            >
              <Pencil className="h-3 w-3" />
              Modifier
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
