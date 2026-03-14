import type { PlannerEvent } from "./types";

/** Visible hours in the grid (7 AM to 10 PM) */
export const HOURS = Array.from({ length: 16 }, (_, i) => i + 7); // [7..22]

export const TOTAL_HOURS = HOURS.length; // 16

/** Returns the Monday of the week containing `date`. */
export function getMonday(date: Date): Date {
  const d = new Date(date);
  const day = d.getDay(); // 0=Sun, 1=Mon...
  const diff = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + diff);
  d.setHours(0, 0, 0, 0);
  return d;
}

/** Shifts a date by `n` weeks. */
export function addWeeks(date: Date, n: number): Date {
  const d = new Date(date);
  d.setDate(d.getDate() + n * 7);
  return d;
}

/** Format: "10 – 16 mars 2026" */
export function formatWeekLabel(monday: Date): string {
  const sunday = addWeeks(monday, 1);
  sunday.setDate(sunday.getDate() - 1);

  const startDay = monday.getDate();
  const endDay = sunday.getDate();
  const monthStart = monday.toLocaleDateString("fr-FR", { month: "long" });
  const monthEnd = sunday.toLocaleDateString("fr-FR", { month: "long" });
  const year = sunday.getFullYear();

  if (monthStart === monthEnd) {
    return `${startDay} – ${endDay} ${monthEnd} ${year}`;
  }
  return `${startDay} ${monthStart} – ${endDay} ${monthEnd} ${year}`;
}

export interface DayColumn {
  date: Date;
  label: string; // "lun. 10"
  iso: string; // "2026-03-10"
  isToday: boolean;
}

/** Returns 7 day descriptors Mon–Sun for the week starting at `monday`. */
export function getDayColumns(monday: Date): DayColumn[] {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const todayISO = toISODate(today);

  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday);
    d.setDate(d.getDate() + i);
    const iso = toISODate(d);
    const label = d.toLocaleDateString("fr-FR", {
      weekday: "short",
      day: "numeric",
    });
    return { date: d, label, iso, isToday: iso === todayISO };
  });
}

/** Groups events by their date (YYYY-MM-DD). */
export function groupEventsByDay(
  events: PlannerEvent[],
  _monday: Date,
): Map<string, PlannerEvent[]> {
  const map = new Map<string, PlannerEvent[]>();
  for (const ev of events) {
    const day = ev.start_at.slice(0, 10); // "YYYY-MM-DD"
    const arr = map.get(day) ?? [];
    arr.push(ev);
    map.set(day, arr);
  }
  return map;
}

/**
 * Given an event, returns CSS top% and height% to position it
 * within a day column spanning HOURS[0]..HOURS[last]+1.
 */
export function eventTopAndHeight(event: PlannerEvent): {
  top: string;
  height: string;
} {
  const startDate = new Date(event.start_at);
  const endDate = new Date(event.end_at);

  const startMinutes =
    (startDate.getHours() - HOURS[0]) * 60 + startDate.getMinutes();
  const endMinutes =
    (endDate.getHours() - HOURS[0]) * 60 + endDate.getMinutes();
  const totalMinutes = TOTAL_HOURS * 60;

  const topPct = Math.max(0, (startMinutes / totalMinutes) * 100);
  const heightPct = Math.max(
    2,
    ((endMinutes - startMinutes) / totalMinutes) * 100,
  );

  return { top: `${topPct}%`, height: `${heightPct}%` };
}

/** Formats a Date to "YYYY-MM-DD" */
export function toISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** Formats hour number to "07:00" display string */
export function formatHour(h: number): string {
  return `${String(h).padStart(2, "0")}:00`;
}
