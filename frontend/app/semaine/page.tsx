"use client";

import { useDashboard } from "@/lib/queries/use-dashboard";

export default function SemainePage() {
  const { data, isLoading, error } = useDashboard();

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
        Erreur de connexion à l&apos;API Python. Vérifiez que le backend FastAPI est bien démarré (BORD_API_PORT).
      </div>
    );
  }

  const summary = data?.week?.summary;
  const events = data?.week?.events ?? [];
  const board = data?.week?.board ?? [];
  const readiness = data?.readiness;

  return (
    <div className="space-y-6">
      {/* Métriques en haut */}
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

      {/* Événements de la semaine */}
      <div className="glass rounded-2xl p-5">
        <h2 className="mb-4 text-lg font-semibold">
          Cette semaine
          <span className="ml-2 text-sm font-normal text-text-muted">
            {events.length} événements
          </span>
        </h2>
        {events.length === 0 ? (
          <p className="text-text-muted">Aucun événement cette semaine.</p>
        ) : (
          <div className="space-y-2">
            {events.slice(0, 15).map((e) => (
              <div
                key={e.id}
                className="flex items-center gap-3 rounded-lg bg-surface-0 px-3 py-2"
              >
                <div
                  className="h-2 w-2 rounded-full"
                  style={{ background: getCategoryColor(e.category) }}
                />
                <span className="flex-1 text-sm">{e.title}</span>
                <span className="text-xs text-text-muted">
                  {formatTime(e.start_at)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Board (kanban simplifié) */}
      <div className="glass rounded-2xl p-5">
        <h2 className="mb-4 text-lg font-semibold">
          Backlog
          <span className="ml-2 text-sm font-normal text-text-muted">
            {board.length} tâches
          </span>
        </h2>
        {board.length === 0 ? (
          <p className="text-text-muted">Aucune tâche en backlog.</p>
        ) : (
          <div className="space-y-2">
            {board.map((t) => (
              <div
                key={t.id}
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
                <span className="text-[10px] uppercase text-text-muted">
                  {t.triage_status?.replace(/_/g, " ")}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

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

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("fr-FR", {
      weekday: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}
