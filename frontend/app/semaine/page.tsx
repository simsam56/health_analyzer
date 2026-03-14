"use client";

import { useState, useMemo } from "react";
import { useDashboard } from "@/lib/queries/use-dashboard";
import { useBoardTasks, useCreateTask } from "@/lib/queries/use-planner";
import { Lightbulb, Plus, ChevronLeft, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import type { PlannerEvent, BoardTask, TriageStatus } from "@/lib/types";

// ── Constantes ────────────────────────────────────────────────────
const START_HOUR = 8;
const END_HOUR = 21;
const HOUR_HEIGHT = 60; // px par heure
const HOURS = Array.from({ length: END_HOUR - START_HOUR }, (_, i) => START_HOUR + i);
const DAYS_FR = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"] as const;

const TRIAGE_COLUMNS: { key: TriageStatus; label: string; color: string }[] = [
  { key: "a_determiner", label: "À déterminer", color: "#94a3b8" },
  { key: "urgent", label: "Urgent", color: "#ef4444" },
  { key: "a_planifier", label: "À planifier", color: "#3b82f6" },
  { key: "non_urgent", label: "Non urgent", color: "#64748b" },
  { key: "termine", label: "Terminé", color: "#22c55e" },
];

const IDEA_CATEGORIES = ["Pro", "Perso", "Projet", "À creuser"] as const;

// ── Helpers ───────────────────────────────────────────────────────

function getCategoryColor(cat: string): string {
  const colors: Record<string, string> = {
    sport: "#22c55e",
    yoga: "#a855f7",
    travail: "#3b82f6",
    formation: "#06b6d4",
    social: "#ec4899",
    lecon: "#f59e0b",
    autre: "#64748b",
  };
  return colors[cat] ?? "#64748b";
}

function getMonday(offset: number): Date {
  const now = new Date();
  const day = now.getDay();
  const diff = now.getDate() - day + (day === 0 ? -6 : 1) + offset * 7;
  const monday = new Date(now);
  monday.setHours(0, 0, 0, 0);
  monday.setDate(diff);
  return monday;
}

function addDays(d: Date, n: number): Date {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function formatWeekLabel(monday: Date): string {
  const sunday = addDays(monday, 6);
  const fmt = (d: Date) =>
    d.toLocaleDateString("fr-FR", { day: "numeric", month: "long" });
  return `${fmt(monday)} — ${fmt(sunday)}`;
}

function hm(d: Date): string {
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

// ── Composant principal ──────────────────────────────────────────

export default function SemainePage() {
  const [weekOffset, setWeekOffset] = useState(0);
  const { data, isLoading, error } = useDashboard();
  const { data: boardData } = useBoardTasks();

  const monday = useMemo(() => getMonday(weekOffset), [weekOffset]);
  const weekDays = useMemo(
    () => Array.from({ length: 7 }, (_, i) => addDays(monday, i)),
    [monday],
  );
  const todayIso = isoDate(new Date());

  // Filtrer les events pour la semaine affichée
  const events = useMemo(() => {
    const all = data?.week?.events ?? [];
    const startIso = isoDate(monday);
    const endIso = isoDate(addDays(monday, 7));
    return all.filter((e) => {
      const d = e.start_at?.slice(0, 10);
      return d && d >= startIso && d < endIso;
    });
  }, [data, monday]);

  const board = boardData?.tasks ?? data?.week?.board ?? [];
  const summary = data?.week?.summary;
  const readiness = data?.readiness;

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent-blue border-t-transparent" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass rounded-2xl p-6 text-center text-accent-red">
        Erreur de connexion à l&apos;API Python. Vérifiez que le serveur tourne
        sur le port 8765.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ── Métriques ─────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <MetricPill
          label="Readiness"
          value={readiness?.score ?? 0}
          unit="/100"
          color={readiness?.color ?? "#64748b"}
        />
        <MetricPill
          label="Sport"
          value={summary?.sante_h ?? 0}
          unit="h"
          color="var(--color-sport)"
        />
        <MetricPill
          label="Travail"
          value={summary?.travail_h ?? 0}
          unit="h"
          color="var(--color-travail)"
        />
        <MetricPill
          label="Social"
          value={summary?.relationnel_h ?? 0}
          unit="h"
          color="var(--color-social)"
        />
      </div>

      {/* ── Calendrier semaine ────────────────────────── */}
      <div className="glass rounded-2xl p-4">
        {/* Navigation */}
        <div className="mb-4 flex items-center justify-between">
          <button
            onClick={() => setWeekOffset((o) => o - 1)}
            className="rounded-lg p-2 text-text-muted transition-colors hover:bg-surface-1 hover:text-text-primary"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setWeekOffset(0)}
              className="rounded-lg px-3 py-1 text-xs font-medium text-text-muted transition-colors hover:bg-surface-1 hover:text-text-primary"
            >
              Aujourd&apos;hui
            </button>
            <h3 className="text-sm font-semibold">{formatWeekLabel(monday)}</h3>
          </div>
          <button
            onClick={() => setWeekOffset((o) => o + 1)}
            className="rounded-lg p-2 text-text-muted transition-colors hover:bg-surface-1 hover:text-text-primary"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>

        {/* Grille calendrier */}
        <div className="overflow-x-auto">
          <div
            className="relative min-w-[800px]"
            style={{
              display: "grid",
              gridTemplateColumns: "50px repeat(7, 1fr)",
            }}
          >
            {/* En-têtes jours */}
            <div /> {/* coin vide */}
            {weekDays.map((d, i) => {
              const isToday = isoDate(d) === todayIso;
              return (
                <div
                  key={i}
                  className={`py-2 text-center text-xs font-bold uppercase tracking-wide ${
                    isToday ? "text-accent-blue" : "text-text-muted"
                  }`}
                >
                  <div>{DAYS_FR[i]}</div>
                  <div
                    className={`mt-0.5 text-lg font-extrabold ${
                      isToday ? "text-accent-blue" : "text-text-primary"
                    }`}
                  >
                    {d.getDate()}
                  </div>
                </div>
              );
            })}

            {/* Lignes d'heures + cellules */}
            {HOURS.map((hour) => (
              <div key={hour} className="contents">
                {/* Label heure */}
                <div className="flex h-[60px] items-start justify-end pr-2 text-[10px] font-medium text-text-muted">
                  {String(hour).padStart(2, "0")}:00
                </div>
                {/* Cellules par jour */}
                {weekDays.map((d, di) => {
                  const dateIso = isoDate(d);
                  const isToday = dateIso === todayIso;
                  return (
                    <div
                      key={di}
                      className={`relative h-[60px] border-t border-l ${
                        di === 6 ? "border-r" : ""
                      } ${hour === HOURS[HOURS.length - 1] ? "border-b" : ""} ${
                        isToday
                          ? "border-accent-blue/20 bg-accent-blue/[0.03]"
                          : "border-white/[0.06]"
                      }`}
                    >
                      {/* Events de cette heure/jour */}
                      {hour === START_HOUR &&
                        events
                          .filter(
                            (ev) => ev.start_at?.slice(0, 10) === dateIso,
                          )
                          .map((ev) => (
                            <EventCard key={ev.id} event={ev} />
                          ))}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Board Kanban ──────────────────────────────── */}
      <KanbanBoard board={board} />

      {/* ── Idées (deuxième fold) ─────────────────────── */}
      <IdeasSection />
    </div>
  );
}

// ── EventCard ─────────────────────────────────────────────────────

function EventCard({ event }: { event: PlannerEvent }) {
  const start = new Date(event.start_at);
  const end = new Date(event.end_at);
  const startHour = start.getHours() + start.getMinutes() / 60;
  const endHour = end.getHours() + end.getMinutes() / 60;

  // Clamp to visible range
  const clampedStart = Math.max(startHour, START_HOUR);
  const clampedEnd = Math.min(endHour, END_HOUR);
  if (clampedEnd <= clampedStart) return null;

  const top = (clampedStart - START_HOUR) * HOUR_HEIGHT;
  const height = Math.max(24, (clampedEnd - clampedStart) * HOUR_HEIGHT - 2);
  const color = getCategoryColor(event.category);

  const durationMin = Math.round((end.getTime() - start.getTime()) / 60000);
  const durLabel =
    durationMin >= 60
      ? `${Math.floor(durationMin / 60)}h${durationMin % 60 ? String(durationMin % 60).padStart(2, "0") : ""}`
      : `${durationMin}min`;

  return (
    <div
      className="absolute inset-x-0.5 z-10 overflow-hidden rounded-md px-1.5 py-1 text-[10px] leading-tight"
      style={{
        top: `${top}px`,
        height: `${height}px`,
        background: `${color}20`,
        borderLeft: `3px solid ${color}`,
      }}
    >
      <div className="truncate font-semibold text-text-primary">
        {event.title}
      </div>
      <div className="text-text-muted">
        {hm(start)} – {hm(end)}
        {height > 30 && ` · ${durLabel}`}
      </div>
    </div>
  );
}

// ── KanbanBoard ───────────────────────────────────────────────────

function KanbanBoard({ board }: { board: BoardTask[] }) {
  const grouped = useMemo(() => {
    const map: Record<string, BoardTask[]> = {};
    for (const col of TRIAGE_COLUMNS) {
      map[col.key] = [];
    }
    for (const task of board) {
      const key = task.triage_status || "a_determiner";
      if (map[key]) map[key].push(task);
      else map["a_determiner"].push(task);
    }
    return map;
  }, [board]);

  return (
    <div className="glass rounded-2xl p-5">
      <h2 className="mb-4 text-lg font-semibold">Mes tâches</h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {TRIAGE_COLUMNS.map((col) => {
          const tasks = grouped[col.key];
          return (
            <div
              key={col.key}
              className="rounded-xl bg-surface-0 p-3"
              style={{ borderTop: `2px solid ${col.color}` }}
            >
              <div className="mb-2 flex items-center justify-between">
                <span
                  className="text-[11px] font-extrabold uppercase tracking-wider"
                  style={{ color: col.color }}
                >
                  {col.label}
                </span>
                <span className="rounded-full bg-surface-1 px-2 py-0.5 text-[10px] font-bold text-text-muted">
                  {tasks.length}
                </span>
              </div>
              {tasks.length === 0 ? (
                <p className="py-2 text-center text-[11px] text-text-muted">
                  —
                </p>
              ) : (
                <div className="space-y-1.5">
                  {tasks.map((t) => (
                    <div
                      key={t.id}
                      className="rounded-lg bg-surface-1 p-2 transition-colors hover:bg-surface-2"
                      style={{
                        borderLeft: `3px solid ${getCategoryColor(t.category)}`,
                      }}
                    >
                      <div className="text-xs font-medium text-text-primary">
                        {t.title}
                      </div>
                      <span
                        className="mt-1 inline-block rounded px-1.5 py-0.5 text-[9px] font-bold uppercase"
                        style={{
                          background: `${getCategoryColor(t.category)}20`,
                          color: getCategoryColor(t.category),
                        }}
                      >
                        {t.category}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── IdeasSection ──────────────────────────────────────────────────

function IdeasSection() {
  const { data } = useBoardTasks();
  const createTask = useCreateTask();
  const [newIdea, setNewIdea] = useState("");
  const [category, setCategory] = useState<string>("Pro");

  const ideas =
    data?.tasks?.filter((t) => t.triage_status === "a_determiner") ?? [];

  const handleAdd = () => {
    if (!newIdea.trim()) return;
    createTask.mutate(
      {
        title: newIdea.trim(),
        category: "autre",
        triage_status: "a_determiner",
        notes: `Catégorie idée : ${category}`,
      },
      {
        onSuccess: () => {
          setNewIdea("");
          toast.success("Idée ajoutée !");
        },
      },
    );
  };

  return (
    <div className="glass rounded-2xl p-5">
      <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold">
        <Lightbulb className="h-5 w-5 text-accent-yellow" />
        Idées
      </h2>

      {/* Formulaire */}
      <div className="mb-4 flex gap-2">
        <input
          type="text"
          value={newIdea}
          onChange={(e) => setNewIdea(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
          placeholder="Nouvelle idée..."
          className="flex-1 rounded-lg bg-surface-0 px-3 py-2 text-sm text-text-primary placeholder-text-muted outline-none focus:ring-1 focus:ring-accent-yellow/50"
        />
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="rounded-lg bg-surface-0 px-2 py-2 text-xs text-text-secondary outline-none"
        >
          {IDEA_CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <button
          onClick={handleAdd}
          disabled={createTask.isPending}
          className="flex items-center gap-1 rounded-lg bg-accent-yellow/20 px-3 py-2 text-sm font-medium text-accent-yellow transition-colors hover:bg-accent-yellow/30 disabled:opacity-50"
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>

      {/* Liste */}
      <div className="text-sm font-medium text-text-muted">
        Mes idées
        <span className="ml-1 text-xs">({ideas.length})</span>
      </div>
      {ideas.length === 0 ? (
        <p className="mt-2 text-sm text-text-muted">
          Aucune idée. Tapez ci-dessus pour capturer.
        </p>
      ) : (
        <div className="mt-2 space-y-1.5">
          {ideas.map((t) => (
            <div
              key={t.id}
              className="flex items-center gap-3 rounded-lg bg-surface-0 px-3 py-2"
            >
              <Lightbulb className="h-3.5 w-3.5 text-accent-yellow" />
              <span className="flex-1 text-sm">{t.title}</span>
              <span className="text-[10px] text-text-muted">
                {new Date(t.created_at).toLocaleDateString("fr-FR", {
                  day: "numeric",
                  month: "short",
                })}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── MetricPill ────────────────────────────────────────────────────

function MetricPill({
  label,
  value,
  unit,
  color,
}: {
  label: string;
  value: number;
  unit: string;
  color: string;
}) {
  return (
    <div className="glass rounded-xl px-4 py-3">
      <div className="text-xs font-medium text-text-muted">{label}</div>
      <div className="mt-1 flex items-baseline gap-1">
        <span className="text-2xl font-bold" style={{ color }}>
          {typeof value === "number" ? value.toFixed(1) : value}
        </span>
        <span className="text-sm text-text-muted">{unit}</span>
      </div>
    </div>
  );
}
