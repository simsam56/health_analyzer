"use client";

import clsx from "clsx";

const PERIODS = [
  { label: "4 sem.", weeks: 4 },
  { label: "8 sem.", weeks: 8 },
  { label: "12 sem.", weeks: 12 },
  { label: "6 mois", weeks: 26 },
];

interface PeriodSelectorProps {
  value: number;
  onChange: (weeks: number) => void;
}

export function PeriodSelector({ value, onChange }: PeriodSelectorProps) {
  return (
    <div className="flex gap-1">
      {PERIODS.map((p) => (
        <button
          key={p.weeks}
          onClick={() => onChange(p.weeks)}
          className={clsx(
            "rounded-lg px-3 py-1 text-xs font-medium transition-colors",
            value === p.weeks
              ? "bg-accent-blue/20 text-accent-blue"
              : "text-text-muted hover:bg-surface-1",
          )}
        >
          {p.label}
        </button>
      ))}
    </div>
  );
}
