"use client";

import { motion } from "framer-motion";
import {
  Heart,
  Activity,
  AlertTriangle,
  AlertCircle,
  TrendingUp,
  Info,
} from "lucide-react";
import clsx from "clsx";
import type { HealthHighlight } from "@/lib/types";
import type { LucideIcon } from "lucide-react";

const ICON_MAP: Record<string, LucideIcon> = {
  heart: Heart,
  activity: Activity,
  "alert-triangle": AlertTriangle,
  "alert-circle": AlertCircle,
  "trending-up": TrendingUp,
  info: Info,
};

const TYPE_STYLES = {
  positive: "bg-accent-green/10 text-accent-green",
  warning: "bg-accent-yellow/10 text-accent-yellow",
  neutral: "bg-surface-1 text-text-secondary",
};

interface HealthHighlightsProps {
  highlights: HealthHighlight[];
}

export function HealthHighlights({ highlights }: HealthHighlightsProps) {
  if (highlights.length === 0) return null;

  return (
    <div className="flex gap-3 overflow-x-auto pb-1 scrollbar-hide">
      {highlights.map((h, i) => {
        const Icon = ICON_MAP[h.icon] ?? Info;
        return (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1 }}
            className={clsx(
              "flex shrink-0 items-center gap-2 rounded-full px-4 py-2 text-sm",
              TYPE_STYLES[h.type],
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            <span>{h.text}</span>
          </motion.div>
        );
      })}
    </div>
  );
}
