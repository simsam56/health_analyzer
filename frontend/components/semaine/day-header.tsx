"use client";

interface DayHeaderProps {
  date: Date;
  isToday: boolean;
  eventCount: number;
}

const DAY_NAMES = ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"];

export function DayHeader({ date, isToday, eventCount }: DayHeaderProps) {
  const dayName = DAY_NAMES[date.getDay()];
  const dayNum = date.getDate();

  return (
    <div className="flex flex-col items-center gap-0.5 py-2">
      <span className="text-[10px] font-medium uppercase text-text-muted">
        {dayName}
      </span>
      <span
        className={`flex h-7 w-7 items-center justify-center rounded-full text-sm font-semibold ${
          isToday
            ? "bg-accent-blue text-white"
            : "text-text-primary"
        }`}
      >
        {dayNum}
      </span>
      {eventCount > 0 && (
        <span className="text-[9px] text-text-muted">{eventCount}</span>
      )}
    </div>
  );
}
