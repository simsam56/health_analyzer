"use client";

import { SOURCE_LABELS } from "@/lib/constants";

interface SourceBadgeProps {
  source: string;
}

export function SourceBadge({ source }: SourceBadgeProps) {
  const label = SOURCE_LABELS[source] ?? source;
  const colors: Record<string, string> = {
    local: "text-accent-blue bg-accent-blue/15",
    apple_calendar: "text-text-muted bg-surface-2",
    google_calendar: "text-accent-red bg-accent-red/15",
  };

  return (
    <span
      className={`rounded px-1 py-0.5 text-[8px] font-medium uppercase leading-none ${colors[source] ?? "text-text-muted bg-surface-2"}`}
    >
      {label}
    </span>
  );
}
