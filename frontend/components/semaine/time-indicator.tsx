"use client";

import { useEffect, useState } from "react";
import { GRID_START_HOUR, GRID_END_HOUR, HOUR_HEIGHT } from "@/lib/constants";

interface TimeIndicatorProps {
  hourHeight?: number;
}

export function TimeIndicator({ hourHeight = HOUR_HEIGHT }: TimeIndicatorProps) {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(interval);
  }, []);

  const hours = now.getHours() + now.getMinutes() / 60;
  if (hours < GRID_START_HOUR || hours > GRID_END_HOUR) return null;

  const top = (hours - GRID_START_HOUR) * hourHeight;

  return (
    <div
      className="pointer-events-none absolute left-0 right-0 z-20"
      style={{ top }}
    >
      <div className="flex items-center">
        <div className="h-2.5 w-2.5 -translate-x-1/2 rounded-full bg-red-500" />
        <div className="h-px flex-1 bg-red-500" />
      </div>
    </div>
  );
}
