/**
 * Types TypeScript — miroir des modèles Pydantic du backend.
 */

// ── Santé ─────────────────────────────────────────────────────────

export interface HealthMetrics {
  hrv: number | null;
  hrv_date: string | null;
  hrv_days_old: number | null;
  hrv_baseline: number | null;
  hrv_freshness: number;
  rhr: number | null;
  rhr_baseline: number | null;
  rhr_date: string | null;
  rhr_days_old: number | null;
  rhr_freshness: number;
  vo2max: number | null;
  vo2max_date: string | null;
  vo2max_days_old: number | null;
  vo2max_freshness: number;
  sleep_h: number | null;
  sleep_date: string | null;
  sleep_days_old: number | null;
  sleep_freshness: number;
  body_battery: number | null;
  body_battery_date: string | null;
  body_battery_days_old: number | null;
  body_battery_freshness: number;
  weight_kg: number | null;
  weight_date: string | null;
  weight_days_old: number | null;
  weight_freshness: number;
}

export interface Ring {
  score: number;
  label: string;
  color: string;
}

export interface RingsData {
  recovery: Ring;
  activity: Ring;
  sleep: Ring;
}

export interface ReadinessData {
  score: number;
  label: string;
  color: string;
  components: Record<string, number>;
  confidence: number;
  freshness: Record<string, number>;
}

// ── Training ──────────────────────────────────────────────────────

export interface PMCPoint {
  date: string;
  ctl: number;
  atl: number;
  tsb: number;
  tss?: number;
}

export interface PMCData {
  current: { ctl: number; atl: number; tsb: number };
  series: PMCPoint[];
}

export interface ACWRData {
  acwr: number;
  acwr_roll: number;
  acwr_ewma: number;
  acute: number;
  chronic: number;
  zone: string;
}

export interface RunningData {
  sessions: number;
  total_km: number;
  km_per_week: number;
  avg_pace: number | null;
  avg_pace_str: string;
  predictions: Record<string, string>;
  pred_10k_confidence: number;
}

// ── Muscles ───────────────────────────────────────────────────────

export interface MuscleZone {
  opacity: number;
  sets_per_week: number;
  total_sets: number;
  total_reps: number;
}

export interface MuscleAlert {
  level: string;
  type: string;
  muscle: string;
  message: string;
  current: number;
  target: number;
  icon?: string;
}

// ── Planner ───────────────────────────────────────────────────────

export type Category =
  | "sport"
  | "yoga"
  | "travail"
  | "formation"
  | "social"
  | "lecon"
  | "autre";

export type TriageStatus =
  | "a_determiner"
  | "urgent"
  | "a_planifier"
  | "non_urgent"
  | "termine";

export interface PlannerEvent {
  id: string;
  task_id: number | null;
  title: string;
  category: Category;
  start_at: string;
  end_at: string;
  notes: string | null;
  source: "local" | "apple_calendar";
  calendar_uid: string | null;
  calendar_name: string | null;
  editable: boolean;
  triage_status: TriageStatus;
  scheduled: boolean;
}

export interface BoardTask {
  id: number;
  title: string;
  category: Category;
  triage_status: TriageStatus;
  notes: string | null;
  created_at: string;
}

// ── Activities ────────────────────────────────────────────────────

export interface Activity {
  id: number;
  source: string;
  type: string;
  name: string | null;
  started_at: string;
  duration_s: number;
  duration_str: string;
  distance_m: number | null;
  distance_km: number | null;
  calories: number | null;
  avg_hr: number | null;
  tss: number | null;
}

// ── Muscles (détail) ─────────────────────────────────────────────

export interface MuscleTarget {
  min: number;
  hyper: number;
  max: number;
  icon: string;
}

export interface MuscleCumulative {
  total_sets: number;
  total_reps: number;
  sets_per_week: number;
  opacity?: number;
}

export interface MuscleSession {
  date: string;
  workout_name: string;
  total_sets: number;
  total_reps: number;
  duration_min: number;
  muscles: string[];
}

export interface MusclesData {
  zones: Record<string, number>;
  cumulative: Record<string, MuscleCumulative>;
  weekly_volume: Record<string, Record<string, unknown>>;
  alerts: MuscleAlert[];
  score: number;
  targets: Record<string, MuscleTarget>;
  top_exercises: Record<string, { exercise: string; sets: number; total_reps: number }[]>;
  recent_sessions: MuscleSession[];
}

// ── Activities (détail) ──────────────────────────────────────────

export interface ActivitiesData {
  recent: Activity[];
  hours_series: { week: string; hours: number }[];
  total_count: number;
  total_km: number;
  strength_sessions: number;
}

// ── Artifact (unified payload) ───────────────────────────────────

export interface ArtifactData {
  ok: boolean;
  generated_at: string;
  health: HealthMetrics;
  readiness: ReadinessData;
  acwr: ACWRData;
  pmc: PMCData;
  running: RunningData;
  muscles: MusclesData;
  week: {
    start: string;
    summary: WeekSummary;
    events: PlannerEvent[];
    board: BoardTask[];
  };
  activities: ActivitiesData;
}

// ── Dashboard (agrégat) ───────────────────────────────────────────

export interface WeekSummary {
  sante_h: number;
  travail_h: number;
  relationnel_h: number;
  apprentissage_h: number;
  autre_h: number;
  total_h: number;
}

export interface DashboardData {
  ok: boolean;
  health: HealthMetrics;
  readiness: ReadinessData;
  acwr: ACWRData;
  pmc: PMCData;
  running: RunningData;
  muscles: {
    zones: Record<string, number>;
    weekly_volume: Record<string, Record<string, unknown>>;
    alerts: MuscleAlert[];
  };
  week: {
    start: string;
    summary: WeekSummary;
    events: PlannerEvent[];
    board: BoardTask[];
  };
  activities: {
    recent: Activity[];
    hours_series: { week: string; hours: number }[];
  };
}
