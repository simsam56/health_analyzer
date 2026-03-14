"use client";

import { useDashboard } from "@/lib/queries/use-dashboard";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { ErrorCard } from "@/components/ui/error-card";
import { ReadinessGauge } from "@/components/dashboard/readiness-gauge";
import { SparkMetric } from "@/components/dashboard/spark-metric";
import { WeeklyHoursChart } from "@/components/dashboard/weekly-hours-chart";
import { PMCMiniChart } from "@/components/dashboard/pmc-mini-chart";
import { EventTimeline } from "@/components/dashboard/event-timeline";
import { BoardKanban } from "@/components/planner/board-kanban";
import { Heart, Activity, Moon, Wind, Battery, TrendingUp } from "lucide-react";

export default function SemainePage() {
  const { data, isLoading, error } = useDashboard();

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorCard />;

  const health = data?.health;
  const readiness = data?.readiness;
  const acwr = data?.acwr;
  const pmc = data?.pmc;
  const events = data?.week?.events ?? [];
  const board = data?.week?.board ?? [];
  const hoursSeries = data?.activities?.hours_series ?? [];
  const summary = data?.week?.summary;

  // Domain hours for the summary pills
  const domainHours = [
    { label: "Sport", value: summary?.sante_h ?? 0, color: "var(--color-sport)" },
    { label: "Travail", value: summary?.travail_h ?? 0, color: "var(--color-travail)" },
    { label: "Social", value: summary?.relationnel_h ?? 0, color: "var(--color-social)" },
    { label: "Formation", value: summary?.apprentissage_h ?? 0, color: "var(--color-formation)" },
  ];

  return (
    <div className="space-y-5">
      {/* ── Row 1: Readiness + Health Metrics ─────────────────────── */}
      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        {/* Readiness gauge */}
        <ReadinessGauge
          score={readiness?.score ?? 0}
          label={readiness?.label ?? "\u2014"}
          color={readiness?.color ?? "#64748b"}
          confidence={readiness?.confidence ?? 0}
          components={readiness?.components}
        />

        {/* Health metric cards */}
        <div className="grid grid-cols-3 gap-2.5">
          <SparkMetric
            icon={Activity}
            label="HRV"
            value={health?.hrv}
            unit="ms"
            color="#22c55e"
            daysOld={health?.hrv_days_old}
          />
          <SparkMetric
            icon={Heart}
            label="FC Repos"
            value={health?.rhr}
            unit="bpm"
            color="#ef4444"
            daysOld={health?.rhr_days_old}
          />
          <SparkMetric
            icon={Moon}
            label="Sommeil"
            value={health?.sleep_h}
            unit="h"
            color="#a855f7"
            daysOld={health?.sleep_days_old}
          />
          <SparkMetric
            icon={Wind}
            label="VO2max"
            value={health?.vo2max}
            unit=""
            color="#06b6d4"
            daysOld={health?.vo2max_days_old}
          />
          <SparkMetric
            icon={Battery}
            label="Body Battery"
            value={health?.body_battery}
            unit="%"
            color="#ff9f0a"
            daysOld={health?.body_battery_days_old}
          />
          <SparkMetric
            icon={TrendingUp}
            label="ACWR"
            value={acwr?.acwr}
            unit=""
            color={
              acwr?.zone === "optimal"
                ? "#22c55e"
                : acwr?.zone === "surcharge"
                  ? "#ff3b30"
                  : "#ff9f0a"
            }
            badge={acwr?.zone}
          />
        </div>
      </div>

      {/* ── Row 2: Domain hours pills ─────────────────────────────── */}
      <div className="grid grid-cols-4 gap-2.5">
        {domainHours.map((d) => (
          <div key={d.label} className="glass rounded-xl px-3.5 py-2.5">
            <div className="text-[10px] font-medium uppercase tracking-wider text-text-muted">
              {d.label}
            </div>
            <div className="mt-0.5 flex items-baseline gap-1">
              <span className="text-xl font-bold tabular-nums" style={{ color: d.color }}>
                {d.value.toFixed(1)}
              </span>
              <span className="text-[10px] text-text-muted">h</span>
            </div>
          </div>
        ))}
      </div>

      {/* ── Row 3: Charts ─────────────────────────────────────────── */}
      <div className="grid gap-4 lg:grid-cols-2">
        <WeeklyHoursChart data={hoursSeries} />
        {pmc && <PMCMiniChart series={pmc.series} current={pmc.current} />}
      </div>

      {/* ── Row 4: Timeline + Board ───────────────────────────────── */}
      <div className="grid gap-4 lg:grid-cols-2">
        <EventTimeline events={events} />
        <BoardKanban tasks={board} />
      </div>
    </div>
  );
}
