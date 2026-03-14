"use client";

interface MetricPillProps {
  label: string;
  value: number;
  unit: string;
  color: string;
}

export function MetricPill({ label, value, unit, color }: MetricPillProps) {
  return (
    <div className="glass rounded-xl px-4 py-3">
      <div className="text-xs font-medium text-text-muted">{label}</div>
      <div className="mt-1 flex items-baseline gap-1">
        <span className="text-2xl font-bold" style={{ color }}>
          {typeof value === "number" ? value.toFixed(1) : value}
        </span>
        <span className="text-sm text-text-muted">{unit}</span>
      </div>
    </div>
  );
}
