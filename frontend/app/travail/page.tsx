"use client";

import { useDashboard } from "@/lib/queries/use-dashboard";
import { Briefcase, TrendingUp } from "lucide-react";

export default function TravailPage() {
  const { data, isLoading } = useDashboard();

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent-blue border-t-transparent" />
      </div>
    );
  }

  const summary = data?.week?.summary;
  const events = data?.week?.events?.filter((e) => e.category === "travail") ?? [];
  const board = data?.week?.board?.filter((t) => t.category === "travail" || t.category === "formation") ?? [];
  const hoursSeries = data?.activities?.hours_series ?? [];
  const workHours = summary?.travail_h ?? 0;
  const targetHours = 40;

  return (
    <div className="space-y-6">
      {/* KPIs */}
      <div className="grid grid-cols-2 gap-3">
        <div className="glass rounded-xl p-4">
          <div className="flex items-center gap-2 text-sm text-text-muted">
            <Briefcase className="h-4 w-4" />
            Heures cette semaine
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-accent-blue">
              {workHours.toFixed(1)}
            </span>
            <span className="text-sm text-text-muted">/ {targetHours}h</span>
          </div>
          <div className="mt-2 h-1.5 w-full rounded-full bg-surface-2">
            <div
              className="h-full rounded-full bg-accent-blue transition-all"
              style={{ width: `${Math.min(100, (workHours / targetHours) * 100)}%` }}
            />
          </div>
        </div>

        <div className="glass rounded-xl p-4">
          <div className="flex items-center gap-2 text-sm text-text-muted">
            <TrendingUp className="h-4 w-4" />
            Formation
          </div>
          <div className="mt-2">
            <span className="text-3xl font-bold text-formation">
              {(summary?.apprentissage_h ?? 0).toFixed(1)}
            </span>
            <span className="text-sm text-text-muted ml-1">h</span>
          </div>
        </div>
      </div>

      {/* Tâches travail cette semaine */}
      <div className="glass rounded-2xl p-5">
        <h3 className="mb-3 text-base font-semibold">Tâches travail cette semaine</h3>
        {events.length === 0 ? (
          <p className="text-text-muted text-sm">Aucune tâche travail planifiée.</p>
        ) : (
          <div className="space-y-2">
            {events.map((e) => (
              <div key={e.id} className="flex items-center gap-3 rounded-lg bg-surface-0 px-3 py-2">
                <div className="h-2 w-2 rounded-full bg-accent-blue" />
                <span className="flex-1 text-sm">{e.title}</span>
                <span className="text-xs text-text-muted">
                  {new Date(e.start_at).toLocaleDateString("fr-FR", { weekday: "short", hour: "2-digit", minute: "2-digit" })}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Backlog travail */}
      {board.length > 0 && (
        <div className="glass rounded-2xl p-5">
          <h3 className="mb-3 text-base font-semibold">
            Backlog travail
            <span className="ml-2 text-sm font-normal text-text-muted">{board.length} tâches</span>
          </h3>
          <div className="space-y-2">
            {board.map((t) => (
              <div key={t.id} className="flex items-center gap-3 rounded-lg bg-surface-0 px-3 py-2">
                <span className="flex-1 text-sm">{t.title}</span>
                <span className="text-[10px] uppercase text-text-muted">
                  {t.triage_status?.replace(/_/g, " ")}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
