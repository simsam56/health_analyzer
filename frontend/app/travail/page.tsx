"use client";

import { useDashboard } from "@/lib/queries/use-dashboard";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { ErrorCard } from "@/components/ui/error-card";
import { BoardKanban } from "@/components/planner/board-kanban";
import { Briefcase, TrendingUp } from "lucide-react";
import { formatTime } from "@/lib/utils";

export default function TravailPage() {
  const { data, isLoading, error } = useDashboard();

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorCard />;

  const summary = data?.week?.summary;
  const events = data?.week?.events?.filter((e) => e.category === "travail") ?? [];
  const board = data?.week?.board?.filter((t) => t.category === "travail" || t.category === "formation") ?? [];
  const workHours = summary?.travail_h ?? 0;
  const targetHours = 40;

  return (
    <div className="space-y-6">
      {/* KPIs */}
      <section aria-label="Indicateurs travail" data-section="kpi-travail">
        <div className="grid grid-cols-2 gap-3">
          <div className="glass rounded-xl p-4" data-metric="heures-travail">
            <div className="flex items-center gap-2 text-sm text-text-muted">
              <Briefcase className="h-4 w-4" aria-hidden="true" />
              Heures cette semaine
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-3xl font-bold text-accent-blue">
                {workHours.toFixed(1)}
              </span>
              <span className="text-sm text-text-muted">/ {targetHours}h</span>
            </div>
            <div
              className="mt-2 h-1.5 w-full rounded-full bg-surface-2"
              role="progressbar"
              aria-valuenow={Math.round(workHours)}
              aria-valuemin={0}
              aria-valuemax={targetHours}
              aria-label={`${workHours.toFixed(1)} heures sur ${targetHours} heures objectif`}
            >
              <div
                className="h-full rounded-full bg-accent-blue transition-all"
                style={{ width: `${Math.min(100, (workHours / targetHours) * 100)}%` }}
              />
            </div>
          </div>

          <div className="glass rounded-xl p-4" data-metric="heures-formation">
            <div className="flex items-center gap-2 text-sm text-text-muted">
              <TrendingUp className="h-4 w-4" aria-hidden="true" />
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
      </section>

      {/* Tâches travail cette semaine */}
      <section aria-label="Tâches travail cette semaine" data-section="taches-travail-semaine">
        <div className="glass rounded-2xl p-5">
          <h3 className="mb-3 text-base font-semibold">Tâches travail cette semaine</h3>
          {events.length === 0 ? (
            <p className="text-text-muted text-sm">Aucune tâche travail planifiée.</p>
          ) : (
            <div className="space-y-2" role="list" aria-label="Événements travail">
              {events.map((e) => (
                <div
                  key={e.id}
                  role="listitem"
                  data-event-id={e.id}
                  className="flex items-center gap-3 rounded-lg bg-surface-0 px-3 py-2"
                >
                  <div className="h-2 w-2 rounded-full bg-accent-blue" aria-hidden="true" />
                  <span className="flex-1 text-sm">{e.title}</span>
                  <span className="text-xs text-text-muted">
                    {formatTime(e.start_at)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {board.length > 0 && (
        <BoardKanban tasks={board} title="Backlog travail" />
      )}
    </div>
  );
}
