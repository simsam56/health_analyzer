"use client";

import { useDashboard } from "@/lib/queries/use-dashboard";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { ErrorCard } from "@/components/ui/error-card";
import { MetricPill } from "@/components/ui/metric-pill";
import { EventList } from "@/components/planner/event-list";
import { BoardKanban } from "@/components/planner/board-kanban";

export default function SemainePage() {
  const { data, isLoading, error } = useDashboard();

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorCard />;

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

      <EventList events={events} />

      <BoardKanban tasks={board} />
    </div>
  );
}
