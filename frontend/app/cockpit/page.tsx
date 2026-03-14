"use client";

import { useArtifact } from "@/lib/queries/use-artifact";
import { ThreeRings } from "@/components/health/three-rings";
import { MetricCard } from "@/components/health/metric-card";
import {
  Heart,
  Activity,
  Moon,
  Wind,
  Battery,
  TrendingUp,
  Footprints,
  Timer,
  Dumbbell,
  Target,
  Zap,
  BarChart3,
} from "lucide-react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
  Cell,
} from "recharts";

// ── Helpers ──────────────────────────────────────────────────────

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

function getActivityIcon(type: string): string {
  const icons: Record<string, string> = {
    Running: "\u{1F3C3}",
    Cycling: "\u{1F6B4}",
    "Strength Training": "\u{1F3CB}\uFE0F",
    Swimming: "\u{1F3CA}",
    Yoga: "\u{1F9D8}",
    Hiking: "\u{1F97E}",
    Walking: "\u{1F6B6}",
  };
  return icons[type] ?? "\u{1F3C3}";
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

function acwrZoneColor(zone: string): string {
  const colors: Record<string, string> = {
    repos: "#64748b",
    "l\u00E9ger": "#3b82f6",
    optimal: "#22c55e",
    "\u00E9lev\u00E9": "#ff9f0a",
    danger: "#ff3b30",
  };
  return colors[zone] ?? "#64748b";
}

function muscleAlertColor(level: string): string {
  const colors: Record<string, string> = {
    critique: "#ff3b30",
    faible: "#ff9f0a",
    ok: "#ffd60a",
    optimal: "#22c55e",
    excessif: "#ff9f0a",
  };
  return colors[level] ?? "#64748b";
}

// ── Page Component ───────────────────────────────────────────────

export default function CockpitPage() {
  const { data, isLoading, error } = useArtifact();

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent-green border-t-transparent" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="glass rounded-2xl p-6 text-center text-accent-red">
        Erreur de connexion. V&eacute;rifiez que le serveur tourne sur le port 8765.
      </div>
    );
  }

  const { health, readiness, acwr, pmc, running, muscles, activities, week } =
    data;

  return (
    <div className="space-y-6">
      {/* ── Row 1: Readiness + Health metrics ── */}
      <div className="grid gap-4 lg:grid-cols-[auto_1fr]">
        {/* Rings + Score */}
        <div className="glass-strong rounded-2xl p-6">
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:gap-6">
            <ThreeRings
              recovery={readiness?.score ?? 0}
              activity={
                acwr ? Math.min(100, Math.max(0, acwr.acwr * 75)) : 0
              }
              sleep={
                health?.sleep_h
                  ? Math.min(100, (health.sleep_h / 8) * 100)
                  : 0
              }
            />
            <div className="text-center sm:text-left">
              <div className="text-sm font-medium text-text-muted">
                Readiness
              </div>
              <div
                className="text-5xl font-extrabold"
                style={{ color: readiness?.color ?? "#64748b" }}
              >
                {readiness?.score ?? "\u2014"}
              </div>
              <div
                className="mt-1 text-sm font-medium"
                style={{ color: readiness?.color ?? "#64748b" }}
              >
                {readiness?.label ?? "\u2014"}
              </div>
              <div className="mt-2 text-xs text-text-muted">
                Confiance : {((readiness?.confidence ?? 0) * 100).toFixed(0)}%
              </div>
            </div>
          </div>
        </div>

        {/* Health metric cards */}
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
      </div>

      {/* ── Row 2: PMC Chart + ACWR gauge ── */}
      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <PMCChart series={pmc?.series ?? []} current={pmc?.current} />
        <ACWRCard acwr={acwr} />
      </div>

      {/* ── Row 3: Activity Hours + Muscle Heatmap ── */}
      <div className="grid gap-4 lg:grid-cols-2">
        <ActivityHoursChart series={activities?.hours_series ?? []} />
        <MuscleHeatmap
          zones={muscles?.zones ?? {}}
          cumulative={muscles?.cumulative ?? {}}
          targets={muscles?.targets ?? {}}
          score={muscles?.score ?? 0}
        />
      </div>

      {/* ── Row 4: Running + Muscle Alerts ── */}
      <div className="grid gap-4 lg:grid-cols-2">
        {running && running.sessions > 0 && <RunningCard running={running} />}
        <MuscleAlerts alerts={muscles?.alerts ?? []} />
      </div>

      {/* ── Row 5: Recent Activities + Week Events ── */}
      <div className="grid gap-4 lg:grid-cols-2">
        <RecentActivities activities={activities?.recent ?? []} />
        <WeekEvents
          events={week?.events ?? []}
          summary={week?.summary}
        />
      </div>

      {/* ── Row 6: Stats totaux ── */}
      <div className="grid grid-cols-3 gap-3">
        <StatPill
          icon={BarChart3}
          label="Activit\u00E9s"
          value={activities?.total_count ?? 0}
        />
        <StatPill
          icon={Footprints}
          label="Kilom\u00E8tres"
          value={activities?.total_km ?? 0}
          unit="km"
        />
        <StatPill
          icon={Dumbbell}
          label="S\u00E9ances muscu"
          value={activities?.strength_sessions ?? 0}
        />
      </div>
    </div>
  );
}

// ── PMC Chart (CTL / ATL / TSB) ──────────────────────────────────

function PMCChart({
  series,
  current,
}: {
  series: { date: string; ctl: number; atl: number; tsb: number; tss?: number }[];
  current?: { ctl: number; atl: number; tsb: number };
}) {
  // Sample to ~45 points for readability
  const step = Math.max(1, Math.floor(series.length / 45));
  const sampled = series.filter((_, i) => i % step === 0 || i === series.length - 1);

  return (
    <div className="glass rounded-2xl p-5">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-base font-semibold">
          <TrendingUp className="h-4 w-4 text-accent-blue" />
          Charge d&apos;entra&icirc;nement (PMC)
        </h3>
        <div className="flex gap-3 text-xs text-text-muted">
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-accent-blue" />
            CTL {current?.ctl?.toFixed(0)}
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-accent-red" />
            ATL {current?.atl?.toFixed(0)}
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-accent-green" />
            TSB {current?.tsb?.toFixed(0)}
          </span>
        </div>
      </div>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={sampled} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="gradCTL" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradTSB" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#22c55e" stopOpacity={0.2} />
                <stop offset="100%" stopColor="#22c55e" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="date"
              tick={{ fill: "#64748b", fontSize: 10 }}
              tickFormatter={(v: string) => {
                const d = new Date(v);
                return `${d.getDate()}/${d.getMonth() + 1}`;
              }}
              interval={Math.max(0, Math.floor(sampled.length / 6))}
            />
            <YAxis tick={{ fill: "#64748b", fontSize: 10 }} />
            <Tooltip
              contentStyle={{
                background: "rgba(10,14,26,0.95)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 8,
                fontSize: 12,
                color: "#f1f5f9",
              }}
              labelFormatter={(v: string) =>
                new Date(v).toLocaleDateString("fr-FR", {
                  day: "numeric",
                  month: "short",
                })
              }
            />
            <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" />
            <Area
              type="monotone"
              dataKey="ctl"
              stroke="#3b82f6"
              fill="url(#gradCTL)"
              strokeWidth={2}
              name="CTL (Forme)"
              dot={false}
            />
            <Area
              type="monotone"
              dataKey="atl"
              stroke="#ff3b30"
              fill="none"
              strokeWidth={1.5}
              strokeDasharray="4 2"
              name="ATL (Fatigue)"
              dot={false}
            />
            <Area
              type="monotone"
              dataKey="tsb"
              stroke="#22c55e"
              fill="url(#gradTSB)"
              strokeWidth={1.5}
              name="TSB (Forme)"
              dot={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ── ACWR Card ────────────────────────────────────────────────────

function ACWRCard({
  acwr,
}: {
  acwr?: {
    acwr: number;
    zone: string;
    acute: number;
    chronic: number;
  };
}) {
  if (!acwr) return null;

  const pct = Math.min(100, Math.max(0, (acwr.acwr / 2) * 100));
  const color = acwrZoneColor(acwr.zone);

  return (
    <div className="glass rounded-2xl p-5">
      <h3 className="mb-4 flex items-center gap-2 text-base font-semibold">
        <Zap className="h-4 w-4" style={{ color }} />
        Ratio Charge (ACWR)
      </h3>

      {/* Gauge */}
      <div className="relative mx-auto mb-4 h-32 w-32">
        <svg viewBox="0 0 120 120" className="h-full w-full">
          {/* Track */}
          <circle
            cx="60"
            cy="60"
            r="50"
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={`${Math.PI * 50 * 0.75} ${Math.PI * 50 * 0.25}`}
            transform="rotate(135 60 60)"
          />
          {/* Value */}
          <circle
            cx="60"
            cy="60"
            r="50"
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={`${(pct / 100) * Math.PI * 50 * 0.75} ${Math.PI * 100}`}
            transform="rotate(135 60 60)"
            style={{ filter: `drop-shadow(0 0 8px ${color}60)` }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold" style={{ color }}>
            {acwr.acwr.toFixed(2)}
          </span>
          <span
            className="text-xs font-medium uppercase"
            style={{ color }}
          >
            {acwr.zone}
          </span>
        </div>
      </div>

      {/* Detail */}
      <div className="grid grid-cols-2 gap-2 text-center">
        <div>
          <div className="text-xs text-text-muted">Aigu (7j)</div>
          <div className="text-sm font-semibold">{acwr.acute.toFixed(1)}</div>
        </div>
        <div>
          <div className="text-xs text-text-muted">Chronique (28j)</div>
          <div className="text-sm font-semibold">{acwr.chronic.toFixed(1)}</div>
        </div>
      </div>

      {/* Zone bar */}
      <div className="mt-4">
        <div className="flex gap-0.5">
          {["repos", "l\u00E9ger", "optimal", "\u00E9lev\u00E9", "danger"].map(
            (z) => (
              <div
                key={z}
                className="h-1.5 flex-1 rounded-full"
                style={{
                  background:
                    acwr.zone === z
                      ? acwrZoneColor(z)
                      : "rgba(255,255,255,0.06)",
                }}
              />
            ),
          )}
        </div>
        <div className="mt-1 flex justify-between text-[9px] text-text-muted">
          <span>0</span>
          <span>0.8</span>
          <span>1.3</span>
          <span>1.5</span>
          <span>2.0</span>
        </div>
      </div>
    </div>
  );
}

// ── Activity Hours Bar Chart ─────────────────────────────────────

function ActivityHoursChart({
  series,
}: {
  series: { week: string; hours: number }[];
}) {
  return (
    <div className="glass rounded-2xl p-5">
      <h3 className="mb-3 flex items-center gap-2 text-base font-semibold">
        <Timer className="h-4 w-4 text-accent-blue" />
        Volume hebdomadaire
      </h3>
      <div className="h-44">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={series} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="week"
              tick={{ fill: "#64748b", fontSize: 10 }}
              tickFormatter={(v: string) => v.replace(/^\d{4}-/, "")}
            />
            <YAxis tick={{ fill: "#64748b", fontSize: 10 }} unit="h" />
            <Tooltip
              contentStyle={{
                background: "rgba(10,14,26,0.95)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 8,
                fontSize: 12,
                color: "#f1f5f9",
              }}
              formatter={(v: number) => [`${v.toFixed(1)}h`, "Heures"]}
            />
            <Bar dataKey="hours" radius={[4, 4, 0, 0]} maxBarSize={32}>
              {series.map((entry, i) => (
                <Cell
                  key={i}
                  fill={
                    i === series.length - 1
                      ? "#3b82f6"
                      : "rgba(59,130,246,0.4)"
                  }
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ── Muscle Heatmap ───────────────────────────────────────────────

function MuscleHeatmap({
  zones,
  cumulative,
  targets,
  score,
}: {
  zones: Record<string, number>;
  cumulative: Record<string, { total_sets?: number; sets_per_week?: number }>;
  targets: Record<string, { min: number; hyper: number; max: number; icon: string }>;
  score: number;
}) {
  const muscles = Object.keys(targets);

  return (
    <div className="glass rounded-2xl p-5">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-base font-semibold">
          <Dumbbell className="h-4 w-4 text-accent-purple" />
          Volume musculaire
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-muted">Score</span>
          <span
            className="text-lg font-bold"
            style={{
              color:
                score >= 70
                  ? "#22c55e"
                  : score >= 40
                    ? "#ff9f0a"
                    : "#ff3b30",
            }}
          >
            {score}
          </span>
        </div>
      </div>

      <div className="space-y-2">
        {muscles.map((mg) => {
          const spw = cumulative[mg]?.sets_per_week ?? 0;
          const target = targets[mg];
          const opacity = zones[mg] ?? 0;
          const pct = Math.min(100, opacity * 100);
          const barColor =
            spw >= target.hyper
              ? "#22c55e"
              : spw >= target.min
                ? "#ff9f0a"
                : spw > 0
                  ? "#ff3b30"
                  : "rgba(255,255,255,0.06)";

          return (
            <div key={mg} className="flex items-center gap-3">
              <span className="w-5 text-center text-sm">{target.icon}</span>
              <span className="w-20 text-xs text-text-secondary">{mg}</span>
              <div className="relative h-3 flex-1 overflow-hidden rounded-full bg-surface-0">
                <div
                  className="absolute inset-y-0 left-0 rounded-full transition-all duration-700"
                  style={{
                    width: `${pct}%`,
                    background: barColor,
                    boxShadow: `0 0 8px ${barColor}40`,
                  }}
                />
                {/* Target line */}
                <div
                  className="absolute inset-y-0 w-px bg-white/30"
                  style={{
                    left: `${Math.min(100, (target.min / target.max) * 100)}%`,
                  }}
                />
              </div>
              <span className="w-16 text-right text-xs font-medium text-text-secondary">
                {spw.toFixed(1)}/{target.hyper}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Running Card ─────────────────────────────────────────────────

function RunningCard({
  running,
}: {
  running: {
    sessions: number;
    total_km: number;
    km_per_week: number;
    avg_pace_str: string;
    predictions: Record<string, string>;
    pred_10k_confidence: number;
  };
}) {
  return (
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
            <div className="text-sm font-semibold text-accent-green">{time}</div>
          </div>
        ))}
      </div>
      <div className="mt-3 text-[10px] text-text-muted">
        Confiance pr&eacute;dictions :{" "}
        {(running.pred_10k_confidence * 100).toFixed(0)}% &bull;{" "}
        {running.sessions} s&eacute;ances &bull; {running.total_km} km total
      </div>
    </div>
  );
}

// ── Muscle Alerts ────────────────────────────────────────────────

function MuscleAlerts({ alerts }: { alerts: { level: string; muscle: string; message: string; current: number; target: number }[] }) {
  const filtered = alerts.filter(
    (a) => a.level === "critique" || a.level === "faible",
  );

  if (filtered.length === 0) {
    return (
      <div className="glass rounded-2xl p-5">
        <h3 className="mb-3 flex items-center gap-2 text-base font-semibold">
          <Target className="h-4 w-4 text-accent-green" />
          Alertes musculaires
        </h3>
        <p className="text-sm text-accent-green">
          Aucune alerte. Tous les volumes sont corrects.
        </p>
      </div>
    );
  }

  return (
    <div className="glass rounded-2xl p-5">
      <h3 className="mb-3 flex items-center gap-2 text-base font-semibold">
        <Target className="h-4 w-4 text-accent-yellow" />
        Alertes musculaires
        <span className="ml-auto text-xs font-normal text-text-muted">
          {filtered.length} alerte{filtered.length > 1 ? "s" : ""}
        </span>
      </h3>
      <div className="space-y-2">
        {filtered.slice(0, 6).map((a, i) => (
          <div
            key={i}
            className="flex items-start gap-2 rounded-lg bg-surface-0 px-3 py-2"
          >
            <div
              className="mt-1 h-2 w-2 shrink-0 rounded-full"
              style={{ background: muscleAlertColor(a.level) }}
            />
            <span className="text-xs text-text-secondary">{a.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Recent Activities ────────────────────────────────────────────

function RecentActivities({
  activities,
}: {
  activities: {
    id: number;
    type: string;
    name: string | null;
    started_at: string;
    duration_str: string;
    distance_km: number | null;
    avg_hr: number | null;
    tss: number | null;
  }[];
}) {
  return (
    <div className="glass rounded-2xl p-5">
      <h3 className="mb-3 flex items-center gap-2 text-base font-semibold">
        <Timer className="h-4 w-4 text-accent-blue" />
        Activit&eacute;s r&eacute;centes
      </h3>
      <div className="space-y-2">
        {activities.slice(0, 8).map((a) => (
          <div
            key={a.id}
            className="flex items-center gap-3 rounded-lg bg-surface-0 px-3 py-2"
          >
            <span className="text-sm">{getActivityIcon(a.type)}</span>
            <div className="flex-1 min-w-0">
              <div className="truncate text-sm font-medium">
                {a.name || a.type}
              </div>
              <div className="text-xs text-text-muted">
                {formatDate(a.started_at)}
                {a.avg_hr ? ` \u2022 ${a.avg_hr} bpm` : ""}
                {a.tss ? ` \u2022 TSS ${a.tss.toFixed(0)}` : ""}
              </div>
            </div>
            <div className="text-right shrink-0">
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
  );
}

// ── Week Events ──────────────────────────────────────────────────

function WeekEvents({
  events,
  summary,
}: {
  events: {
    id: string;
    title: string;
    category: string;
    start_at: string;
  }[];
  summary?: {
    sante_h: number;
    travail_h: number;
    relationnel_h: number;
    total_h: number;
  };
}) {
  return (
    <div className="glass rounded-2xl p-5">
      <h3 className="mb-3 flex items-center justify-between text-base font-semibold">
        <span className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-accent-green" />
          Cette semaine
        </span>
        {summary && (
          <span className="text-xs font-normal text-text-muted">
            {summary.total_h.toFixed(1)}h total
          </span>
        )}
      </h3>

      {/* Summary pills */}
      {summary && (
        <div className="mb-3 flex gap-2">
          {[
            { label: "Sport", val: summary.sante_h, color: "#22c55e" },
            { label: "Travail", val: summary.travail_h, color: "#3b82f6" },
            { label: "Social", val: summary.relationnel_h, color: "#ec4899" },
          ].map(
            (s) =>
              s.val > 0 && (
                <span
                  key={s.label}
                  className="rounded-md px-2 py-0.5 text-[10px] font-medium"
                  style={{
                    background: `${s.color}20`,
                    color: s.color,
                  }}
                >
                  {s.label} {s.val.toFixed(1)}h
                </span>
              ),
          )}
        </div>
      )}

      {events.length === 0 ? (
        <p className="text-text-muted text-sm">Aucun &eacute;v&eacute;nement cette semaine.</p>
      ) : (
        <div className="space-y-1.5">
          {events.slice(0, 10).map((e) => (
            <div
              key={e.id}
              className="flex items-center gap-2 rounded-lg bg-surface-0 px-3 py-1.5"
            >
              <div
                className="h-2 w-2 shrink-0 rounded-full"
                style={{ background: getCategoryColor(e.category) }}
              />
              <span className="flex-1 truncate text-sm">{e.title}</span>
              <span className="text-[10px] text-text-muted">
                {formatWeekday(e.start_at)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function formatWeekday(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("fr-FR", {
      weekday: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

// ── Stat Pill ────────────────────────────────────────────────────

function StatPill({
  icon: Icon,
  label,
  value,
  unit,
}: {
  icon: typeof BarChart3;
  label: string;
  value: number;
  unit?: string;
}) {
  return (
    <div className="glass rounded-xl px-4 py-3 text-center">
      <Icon className="mx-auto mb-1 h-4 w-4 text-text-muted" />
      <div className="text-xl font-bold text-text-primary">
        {typeof value === "number"
          ? value >= 1000
            ? `${(value / 1000).toFixed(1)}k`
            : value
          : value}
        {unit && <span className="ml-1 text-xs text-text-muted">{unit}</span>}
      </div>
      <div className="text-[10px] text-text-muted">{label}</div>
    </div>
  );
}
