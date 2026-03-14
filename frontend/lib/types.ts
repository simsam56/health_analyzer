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
  source: "local" | "apple_calendar" | "google_calendar";
  calendar_uid: string | null;
  calendar_name: string | null;
  editable: boolean;
  triage_status: TriageStatus;
  scheduled: boolean;
  conflict?: string | null;
}

// ── Calendar sync ────────────────────────────────────────────────

export interface CalendarServiceStatus {
  connected: boolean;
  permission: string;
  error: string | null;
  calendars_count: number;
  default_calendar: string | null;
  last_sync_at: string | null;
}

export interface CalendarSyncStatus {
  apple: CalendarServiceStatus;
  google: { connected: false; error: null };
}

export type IdeaCategory = "Pro" | "Perso" | "Projet" | "À creuser";

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
