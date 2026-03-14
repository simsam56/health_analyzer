"use client";

import { RadialBarChart, RadialBar, PolarAngleAxis } from "recharts";

interface ReadinessGaugeProps {
  score: number;
  label: string;
  color: string;
  confidence: number;
  components?: Record<string, number>;
}

export function ReadinessGauge({
  score,
  label,
  color,
  confidence,
  components,
}: ReadinessGaugeProps) {
  const data = [{ value: score, fill: color }];

  return (
    <div className="glass-strong rounded-2xl p-6">
      <div className="flex flex-col items-center gap-4 sm:flex-row sm:gap-8">
        {/* Radial gauge */}
        <div className="relative">
          <RadialBarChart
            width={180}
            height={180}
            cx={90}
            cy={90}
            innerRadius={60}
            outerRadius={80}
            barSize={12}
            data={data}
            startAngle={225}
            endAngle={-45}
          >
            <PolarAngleAxis
              type="number"
              domain={[0, 100]}
              angleAxisId={0}
              tick={false}
            />
            <RadialBar
              dataKey="value"
              cornerRadius={6}
              background={{ fill: "rgba(255,255,255,0.06)" }}
            />
          </RadialBarChart>
          {/* Center text overlay */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span
              className="text-4xl font-extrabold tabular-nums"
              style={{ color }}
            >
              {score}
            </span>
            <span className="text-[11px] font-medium text-text-muted">
              /100
            </span>
          </div>
        </div>

        {/* Info */}
        <div className="flex flex-col gap-3 text-center sm:text-left">
          <div>
            <div className="text-xs font-medium uppercase tracking-wider text-text-muted">
              Readiness
            </div>
            <div className="mt-1 text-lg font-bold" style={{ color }}>
              {label}
            </div>
            <div className="mt-0.5 text-[11px] text-text-muted">
              Confiance {(confidence * 100).toFixed(0)}%
            </div>
          </div>

          {/* Component breakdown */}
          {components && Object.keys(components).length > 0 && (
            <div className="flex flex-wrap gap-x-4 gap-y-1.5">
              {Object.entries(components).map(([key, val]) => (
                <div key={key} className="flex items-center gap-1.5">
                  <div
                    className="h-1.5 w-1.5 rounded-full"
                    style={{
                      background:
                        val >= 70 ? "#22c55e" : val >= 40 ? "#ff9f0a" : "#ff3b30",
                    }}
                  />
                  <span className="text-[10px] text-text-muted capitalize">
                    {key}
                  </span>
                  <span className="text-[10px] font-semibold text-text-secondary tabular-nums">
                    {val.toFixed(0)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
