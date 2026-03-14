"use client";

import { useMemo } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  ReferenceLine,
  Tooltip,
  XAxis,
} from "recharts";
import type { PMCPoint } from "@/lib/types";

interface TSBMiniChartProps {
  series: PMCPoint[];
}

export function TSBMiniChart({ series }: TSBMiniChartProps) {
  const data = useMemo(() => {
    const last60 = series.slice(-60);
    return last60.map((p) => ({
      date: p.date.slice(5), // MM-DD
      tsb: p.tsb,
    }));
  }, [series]);

  if (data.length === 0) {
    return (
      <div className="glass rounded-2xl p-4 text-center text-sm text-text-muted">
        Pas de données TSB
      </div>
    );
  }

  const currentTsb = data[data.length - 1]?.tsb ?? 0;

  return (
    <div className="glass rounded-2xl p-4">
      <div className="mb-2 flex items-center justify-between">
        <h4 className="text-sm font-semibold text-text-primary">Forme (TSB)</h4>
        <span className={`text-lg font-bold ${currentTsb >= 0 ? "text-accent-green" : "text-accent-red"}`}>
          {currentTsb > 0 ? "+" : ""}{currentTsb.toFixed(1)}
        </span>
      </div>
      <div className="h-[80px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id="tsbGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--color-accent-green)" stopOpacity={0.3} />
                <stop offset="50%" stopColor="transparent" stopOpacity={0} />
                <stop offset="100%" stopColor="var(--color-accent-red)" stopOpacity={0.3} />
              </linearGradient>
            </defs>
            <XAxis dataKey="date" hide />
            <Tooltip
              contentStyle={{
                background: "rgba(10,14,26,0.9)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 8,
                fontSize: 12,
              }}
              labelStyle={{ color: "var(--color-text-muted)" }}
            />
            <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" strokeDasharray="3 3" />
            <Area
              type="monotone"
              dataKey="tsb"
              stroke="var(--color-accent-blue)"
              strokeWidth={1.5}
              fill="url(#tsbGrad)"
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-1 text-center text-[10px] text-text-muted">
        {currentTsb >= 0 ? "Frais" : "Fatigué"} — 60 derniers jours
      </div>
    </div>
  );
}
