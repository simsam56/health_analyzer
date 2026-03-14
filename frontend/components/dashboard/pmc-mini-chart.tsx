"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import type { PMCPoint } from "@/lib/types";

interface PMCMiniChartProps {
  series: PMCPoint[];
  current: { ctl: number; atl: number; tsb: number };
}

export function PMCMiniChart({ series, current }: PMCMiniChartProps) {
  if (!series.length) return null;

  // Show last 60 days for the mini chart
  const data = series.slice(-60);

  return (
    <div className="glass rounded-2xl p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-text-muted">
          PMC — Forme & fatigue
        </h3>
        <div className="flex gap-3">
          <div className="flex items-center gap-1">
            <div className="h-1.5 w-1.5 rounded-full bg-accent-blue" />
            <span className="text-[10px] text-text-muted">
              CTL {current.ctl.toFixed(0)}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <div className="h-1.5 w-1.5 rounded-full bg-accent-pink" />
            <span className="text-[10px] text-text-muted">
              ATL {current.atl.toFixed(0)}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <div className="h-1.5 w-1.5 rounded-full bg-accent-green" />
            <span className="text-[10px] text-text-muted">
              TSB {current.tsb > 0 ? "+" : ""}{current.tsb.toFixed(0)}
            </span>
          </div>
        </div>
      </div>
      <div className="h-40">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="gradCTL" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradATL" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#ec4899" stopOpacity={0.2} />
                <stop offset="100%" stopColor="#ec4899" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(255,255,255,0.04)"
              vertical={false}
            />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 9, fill: "#64748b" }}
              tickLine={false}
              axisLine={false}
              interval="preserveStartEnd"
              tickFormatter={(v: string) => {
                const d = new Date(v);
                return `${d.getDate()}/${d.getMonth() + 1}`;
              }}
            />
            <YAxis
              tick={{ fontSize: 9, fill: "#64748b" }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              contentStyle={{
                background: "rgba(10,14,26,0.95)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "8px",
                fontSize: "11px",
                color: "#f1f5f9",
              }}
            />
            <ReferenceLine y={0} stroke="rgba(255,255,255,0.1)" />
            <Area
              type="monotone"
              dataKey="ctl"
              stroke="#3b82f6"
              strokeWidth={1.5}
              fill="url(#gradCTL)"
              name="CTL (Forme)"
            />
            <Area
              type="monotone"
              dataKey="atl"
              stroke="#ec4899"
              strokeWidth={1.5}
              fill="url(#gradATL)"
              name="ATL (Fatigue)"
            />
            <Area
              type="monotone"
              dataKey="tsb"
              stroke="#22c55e"
              strokeWidth={1}
              strokeDasharray="4 2"
              fill="none"
              name="TSB (Forme nette)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
