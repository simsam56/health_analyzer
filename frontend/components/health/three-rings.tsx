"use client";

import { motion } from "framer-motion";

interface ThreeRingsProps {
  recovery: number; // 0-100
  activity: number; // 0-100
  sleep: number; // 0-100
}

const RINGS = [
  { key: "recovery", color: "#30d158", radius: 70, label: "Récupération" },
  { key: "activity", color: "#3b82f6", radius: 55, label: "Activité" },
  { key: "sleep", color: "#a855f7", radius: 40, label: "Sommeil" },
] as const;

export function ThreeRings({ recovery, activity, sleep }: ThreeRingsProps) {
  const values = { recovery, activity, sleep };

  return (
    <div className="relative h-44 w-44">
      <svg viewBox="0 0 160 160" className="h-full w-full">
        {RINGS.map(({ key, color, radius }) => {
          const circumference = 2 * Math.PI * radius;
          const value = values[key as keyof typeof values];
          const offset = circumference - (value / 100) * circumference;

          return (
            <g key={key}>
              {/* Track */}
              <circle
                cx="80"
                cy="80"
                r={radius}
                fill="none"
                stroke="rgba(255,255,255,0.06)"
                strokeWidth="8"
                strokeLinecap="round"
              />
              {/* Value */}
              <motion.circle
                cx="80"
                cy="80"
                r={radius}
                fill="none"
                stroke={color}
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={circumference}
                initial={{ strokeDashoffset: circumference }}
                animate={{ strokeDashoffset: offset }}
                transition={{ duration: 1.2, ease: "easeOut" }}
                transform="rotate(-90 80 80)"
                style={{
                  filter: `drop-shadow(0 0 6px ${color}40)`,
                }}
              />
            </g>
          );
        })}
      </svg>
      {/* Labels sous les rings */}
      <div className="absolute -bottom-6 left-0 right-0 flex justify-center gap-3">
        {RINGS.map(({ key, color, label }) => (
          <div key={key} className="flex items-center gap-1">
            <div
              className="h-1.5 w-1.5 rounded-full"
              style={{ background: color }}
            />
            <span className="text-[10px] text-text-muted">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
