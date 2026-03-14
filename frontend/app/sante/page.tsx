"use client";

import { Suspense, lazy, useState } from "react";
import { useDashboard } from "@/lib/queries/use-dashboard";
import {
  useHealthHighlights,
  useWeeklyTrends,
  useWeeklyLoad,
  usePredictionHistory,
} from "@/lib/queries/use-health";
import { HealthHighlights } from "@/components/health/health-highlights";
import { TrendPillRow } from "@/components/health/trend-pill-row";
import { TrendChart } from "@/components/health/trend-chart";
import { TrainingLoadChart } from "@/components/health/training-load-chart";
import { ACWRGauge } from "@/components/health/acwr-gauge";
import { TSBMiniChart } from "@/components/health/tsb-mini-chart";
import { ActivityJournal } from "@/components/health/activity-journal";
import { PredictionCard } from "@/components/health/prediction-card";
import { FadeInSection } from "@/components/health/fade-in-section";
import { SectionSkeleton } from "@/components/health/section-skeleton";

const MuscleMap = lazy(() => import("@/components/health/muscle-map"));

export default function SantePage() {
  const [trendWeeks, setTrendWeeks] = useState(8);
  const { data: dashboard, isLoading: dashLoading, error: dashError } = useDashboard();
  const { data: highlightsData } = useHealthHighlights();
  const { data: trendsData, isLoading: trendsLoading } = useWeeklyTrends(trendWeeks);
  const { data: loadData } = useWeeklyLoad();
  const { data: predData } = usePredictionHistory();

  if (dashLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent-green border-t-transparent" />
      </div>
    );
  }

  if (dashError) {
    return (
      <div className="glass rounded-2xl p-6 text-center text-accent-red">
        Erreur de connexion à l&apos;API.
      </div>
    );
  }

  const highlights = highlightsData?.highlights ?? [];
  const trends = trendsData?.trends ?? [];
  const weeklyLoad = loadData?.series ?? [];
  const predHistory = predData?.series ?? [];

  return (
    <div className="space-y-6">
      {/* Debug banner - confirms new page is loaded */}
      <div className="rounded-xl bg-accent-green/20 border border-accent-green/40 px-4 py-3 text-center text-sm font-medium text-accent-green">
        Nouvelle page Santé v2 chargée avec succès
      </div>

      {/* 1. Highlights intelligents */}
      {highlights.length > 0 && (
        <FadeInSection delay={0}>
          <HealthHighlights highlights={highlights} />
        </FadeInSection>
      )}

      {/* 2. KPI Pills avec sparklines */}
      <FadeInSection delay={0.08}>
        {trendsLoading ? (
          <SectionSkeleton variant="pills" />
        ) : trends.length > 0 ? (
          <TrendPillRow trends={trends} />
        ) : (
          <div className="text-center text-sm text-text-muted">
            Pas de données de tendances disponibles
          </div>
        )}
      </FadeInSection>

      {/* 3. Courbes de tendances détaillées */}
      <FadeInSection delay={0.16}>
        {trends.length > 0 ? (
          <TrendChart
            trends={trends}
            weeks={trendWeeks}
            onWeeksChange={setTrendWeeks}
          />
        ) : (
          <SectionSkeleton variant="chart" />
        )}
      </FadeInSection>

      {/* 4. Charge d'entraînement */}
      <FadeInSection delay={0.24}>
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <TrainingLoadChart data={weeklyLoad} />
          </div>
          <div className="space-y-4">
            <ACWRGauge acwr={dashboard?.acwr} />
            <TSBMiniChart series={dashboard?.pmc?.series ?? []} />
          </div>
        </div>
      </FadeInSection>

      {/* 5. Muscle Map */}
      <FadeInSection delay={0.32}>
        <Suspense fallback={<SectionSkeleton variant="map" />}>
          <MuscleMap
            zones={dashboard?.muscles?.zones ?? {}}
            weeklyVolume={dashboard?.muscles?.weekly_volume ?? {}}
            alerts={dashboard?.muscles?.alerts ?? []}
          />
        </Suspense>
      </FadeInSection>

      {/* 6. Activités & Prédictions course */}
      <FadeInSection delay={0.40}>
        <div className="grid gap-4 lg:grid-cols-2">
          <ActivityJournal activities={dashboard?.activities?.recent ?? []} />
          <PredictionCard
            running={dashboard?.running}
            predictionHistory={predHistory}
          />
        </div>
      </FadeInSection>
    </div>
  );
}
