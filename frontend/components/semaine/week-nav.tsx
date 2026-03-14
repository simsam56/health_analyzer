"use client";

import { ChevronLeft, ChevronRight, RefreshCw } from "lucide-react";
import { useSyncCalendar } from "@/lib/queries/use-planner";
import { addWeeks, formatWeekLabel, getMonday } from "@/lib/week-utils";

interface WeekNavProps {
  currentMonday: Date;
  onChange: (monday: Date) => void;
}

export function WeekNav({ currentMonday, onChange }: WeekNavProps) {
  const sync = useSyncCalendar();
  const thisMonday = getMonday(new Date());
  const isCurrentWeek =
    currentMonday.getTime() === thisMonday.getTime();

  return (
    <div className="glass flex items-center justify-between rounded-xl px-4 py-2">
      <div className="flex items-center gap-2">
        <button
          onClick={() => onChange(addWeeks(currentMonday, -1))}
          className="rounded-lg p-1.5 hover:bg-surface-2 transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <button
          onClick={() => onChange(addWeeks(currentMonday, 1))}
          className="rounded-lg p-1.5 hover:bg-surface-2 transition-colors"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
        {!isCurrentWeek && (
          <button
            onClick={() => onChange(thisMonday)}
            className="rounded-lg bg-surface-1 px-2.5 py-1 text-xs font-medium text-text-secondary hover:bg-surface-2 transition-colors"
          >
            Aujourd&apos;hui
          </button>
        )}
      </div>

      <span className="text-sm font-semibold text-text-primary">
        {formatWeekLabel(currentMonday)}
      </span>

      <button
        onClick={() => sync.mutate()}
        disabled={sync.isPending}
        className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs text-text-muted hover:bg-surface-2 transition-colors disabled:opacity-50"
      >
        <RefreshCw
          className={`h-3.5 w-3.5 ${sync.isPending ? "animate-spin" : ""}`}
        />
        Sync
      </button>
    </div>
  );
}
