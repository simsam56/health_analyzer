"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  Tooltip,
} from "recharts";
import { Footprints } from "lucide-react";
import type { RunningData, PredictionHistoryPoint } from "@/lib/types";

const DISTANCES = ["5km", "10km", "Semi", "Marathon"] as const;

interface PredictionCardProps {
  running: RunningData | undefined;
  predictionHistory: PredictionHistoryPoint[];
}

export function PredictionCard({ running, predictionHistory }: PredictionCardProps) {
  if (!running || running.sessions === 0) {
    return (
      <div className="glass rounded-2xl p-5 text-center text-sm text-text-muted">
        Pas assez de courses pour prédire
      </div>
    );
  }

  const predictions = running.predictions ?? {};
  const confidence = running.pred_10k_confidence ?? 0;
  const historyData = predictionHistory.filter((p) => p.pred_10k_min !== null);

  return (
    <div className="glass rounded-2xl p-5">
      <h3 className="mb-3 flex items-center gap-2 text-base font-semibold text-text-primary">
        <Footprints className="h-4 w-4 text-accent-green" />
        Prédictions course
      </h3>

      {/* Prediction pills */}
      <div className="mb-3 grid grid-cols-2 gap-2">
        {DISTANCES.map((dist) => (
          <div key={dist} className="rounded-lg bg-surface-0 px-3 py-2">
            <div className="text-xs text-text-muted">{dist}</div>
            <div className="text-sm font-semibold text-accent-green">
              {predictions[dist] ?? "—"}
            </div>
          </div>
        ))}
      </div>

      {/* Confidence + context */}
      <div className="mb-3 flex items-center gap-4 text-xs text-text-muted">
        <span>Confiance : {Math.round(confidence * 100)}%</span>
        <span>{running.avg_pace_str}/km</span>
        <span>{running.km_per_week} km/sem</span>
      </div>

      {/* 10K evolution chart */}
      {historyData.length > 1 && (
        <div>
          <div className="mb-1 text-xs text-text-muted">Évolution 10K</div>
          <div className="h-[70px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={historyData}>
                <XAxis
                  dataKey="month"
                  tick={{ fill: "var(--color-text-muted)", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "rgba(10,14,26,0.9)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  formatter={(val) => [`${Number(val).toFixed(1)} min`, "10K"]}
                  labelStyle={{ color: "var(--color-text-muted)" }}
                />
                <Line
                  type="monotone"
                  dataKey="pred_10k_min"
                  stroke="var(--color-accent-green)"
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
