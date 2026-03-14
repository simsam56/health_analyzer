"use client";

import { useDashboard } from "@/lib/queries/use-dashboard";
import { ThreeRings } from "@/components/health/three-rings";
import { MetricCard } from "@/components/health/metric-card";
import {
  Heart,
  Activity,
  Moon,
  Wind,
  Battery,
  Footprints,
  Timer,
  TrendingUp,
} from "lucide-react";

export default function SantePage() {
  const { data, isLoading, error } = useDashboard();

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent-green border-t-transparent" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass rounded-2xl p-6 text-center text-accent-red">
        Erreur de connexion à l&apos;API.
      </div>
    );
  }

  const health = data?.health;
  const readiness = data?.readiness;
  const acwr = data?.acwr;
  const running = data?.running;
  const recent = data?.activities?.recent ?? [];

  return (
    <div className="space-y-6">
      {/* Rings + Readiness */}
      <div className="glass-strong rounded-2xl p-6">
        <div className="flex flex-col items-center gap-6 sm:flex-row sm:justify-around">
          <ThreeRings
            recovery={readiness?.score ?? 0}
            activity={acwr ? Math.min(100, Math.max(0, acwr.acwr * 75)) : 0}
            sleep={health?.sleep_h ? Math.min(100, (health.sleep_h / 8) * 100) : 0}
          />
          <div className="text-center sm:text-left">
            <div className="text-sm font-medium text-text-muted">Readiness</div>
            <div
              className="text-5xl font-extrabold"
              style={{ color: readiness?.color ?? "#64748b" }}
            >
              {readiness?.score ?? "—"}
            </div>
            <div
              className="mt-1 text-sm font-medium"
              style={{ color: readiness?.color ?? "#64748b" }}
            >
              {readiness?.label ?? "—"}
            </div>
            <div className="mt-2 text-xs text-text-muted">
              Confiance : {((readiness?.confidence ?? 0) * 100).toFixed(0)}%
            </div>
          </div>
        </div>
      </div>

      {/* Métriques santé */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <MetricCard
          icon={Activity}
          label="HRV"
          value={health?.hrv}
          unit="ms"
          daysOld={health?.hrv_days_old}
          freshness={health?.hrv_freshness ?? 0}
        />
        <MetricCard
          icon={Heart}
          label="FC Repos"
          value={health?.rhr}
          unit="bpm"
          daysOld={health?.rhr_days_old}
          freshness={health?.rhr_freshness ?? 0}
        />
        <MetricCard
          icon={Moon}
          label="Sommeil"
          value={health?.sleep_h}
          unit="h"
          daysOld={health?.sleep_days_old}
          freshness={health?.sleep_freshness ?? 0}
        />
        <MetricCard
          icon={Wind}
          label="VO2max"
          value={health?.vo2max}
          unit=""
          daysOld={health?.vo2max_days_old}
          freshness={health?.vo2max_freshness ?? 0}
        />
        <MetricCard
          icon={Battery}
          label="Body Battery"
          value={health?.body_battery}
          unit="%"
          daysOld={health?.body_battery_days_old}
          freshness={health?.body_battery_freshness ?? 0}
        />
        <MetricCard
          icon={TrendingUp}
          label="ACWR"
          value={acwr?.acwr}
          unit=""
          freshness={1}
          badge={acwr?.zone}
        />
      </div>

      {/* Running + Activités récentes */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Running */}
        {running && running.sessions > 0 && (
          <div className="glass rounded-2xl p-5">
            <h3 className="mb-3 flex items-center gap-2 text-base font-semibold">
              <Footprints className="h-4 w-4 text-accent-green" />
              Running
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="text-xs text-text-muted">Allure moy.</div>
                <div className="text-lg font-bold">{running.avg_pace_str}</div>
              </div>
              <div>
                <div className="text-xs text-text-muted">km/sem</div>
                <div className="text-lg font-bold">{running.km_per_week}</div>
              </div>
              {Object.entries(running.predictions).map(([dist, time]) => (
                <div key={dist}>
                  <div className="text-xs text-text-muted">{dist}</div>
                  <div className="text-sm font-semibold text-accent-green">
                    {time}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Activités récentes */}
        <div className="glass rounded-2xl p-5">
          <h3 className="mb-3 flex items-center gap-2 text-base font-semibold">
            <Timer className="h-4 w-4 text-accent-blue" />
            Activités récentes
          </h3>
          <div className="space-y-2">
            {recent.slice(0, 5).map((a) => (
              <div
                key={a.id}
                className="flex items-center gap-3 rounded-lg bg-surface-0 px-3 py-2"
              >
                <span className="text-sm">{getActivityIcon(a.type)}</span>
                <div className="flex-1">
                  <div className="text-sm font-medium">
                    {a.name || a.type}
                  </div>
                  <div className="text-xs text-text-muted">
                    {formatDate(a.started_at)}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-semibold">{a.duration_str}</div>
                  {a.distance_km && (
                    <div className="text-xs text-text-muted">
                      {a.distance_km} km
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function getActivityIcon(type: string): string {
  const icons: Record<string, string> = {
    Running: "🏃",
    Cycling: "🚴",
    "Strength Training": "🏋️",
    Swimming: "🏊",
    Yoga: "🧘",
    Hiking: "🥾",
    Walking: "🚶",
  };
  return icons[type] ?? "🏃";
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("fr-FR", {
      day: "numeric",
      month: "short",
    });
  } catch {
    return "";
  }
}
