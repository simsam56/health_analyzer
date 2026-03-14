"use client";

import { useDashboard } from "@/lib/queries/use-dashboard";
import { Users } from "lucide-react";

export default function SocialPage() {
  const { data, isLoading } = useDashboard();

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent-pink border-t-transparent" />
      </div>
    );
  }

  const summary = data?.week?.summary;
  const events = data?.week?.events?.filter((e) => e.category === "social") ?? [];
  const socialHours = summary?.relationnel_h ?? 0;

  return (
    <div className="space-y-6">
      {/* KPI */}
      <div className="glass rounded-xl p-4">
        <div className="flex items-center gap-2 text-sm text-text-muted">
          <Users className="h-4 w-4" />
          Heures sociales cette semaine
        </div>
        <div className="mt-2">
          <span className="text-3xl font-bold text-accent-pink">
            {socialHours.toFixed(1)}
          </span>
          <span className="text-sm text-text-muted ml-1">h</span>
        </div>
      </div>

      {/* Événements sociaux */}
      <div className="glass rounded-2xl p-5">
        <h3 className="mb-3 text-base font-semibold">Événements sociaux</h3>
        {events.length === 0 ? (
          <p className="text-text-muted text-sm">Aucun événement social cette semaine.</p>
        ) : (
          <div className="space-y-2">
            {events.map((e) => (
              <div key={e.id} className="flex items-center gap-3 rounded-lg bg-surface-0 px-3 py-2">
                <div className="h-2 w-2 rounded-full bg-accent-pink" />
                <span className="flex-1 text-sm">{e.title}</span>
                <span className="text-xs text-text-muted">
                  {new Date(e.start_at).toLocaleDateString("fr-FR", { weekday: "short", day: "numeric" })}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Placeholder contacts */}
      <div className="glass rounded-2xl p-5 text-center">
        <p className="text-text-muted text-sm">
          🚧 Suivi des contacts avec alertes ({">"} 30j, {">"} 60j) — prochaine version.
        </p>
      </div>
    </div>
  );
}
