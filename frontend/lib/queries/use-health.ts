/**
 * React-query hooks pour les nouveaux endpoints santé.
 */

import { useQuery } from "@tanstack/react-query";
import { fetchAPI } from "@/lib/api";
import type {
  HealthHighlight,
  WeeklyTrend,
  WeeklyLoadBreakdown,
  ActivityGroup,
  PredictionHistoryPoint,
} from "@/lib/types";

export function useHealthHighlights() {
  return useQuery<{ ok: boolean; highlights: HealthHighlight[] }>({
    queryKey: ["health-highlights"],
    queryFn: () => fetchAPI("/health/highlights"),
    staleTime: 10 * 60 * 1000,
  });
}

export function useWeeklyTrends(weeks: number = 8) {
  return useQuery<{ ok: boolean; trends: WeeklyTrend[] }>({
    queryKey: ["weekly-trends", weeks],
    queryFn: () => fetchAPI(`/health/weekly-trends?weeks=${weeks}`),
    staleTime: 5 * 60 * 1000,
  });
}

export function useWeeklyLoad(weeks: number = 12) {
  return useQuery<{ ok: boolean; series: WeeklyLoadBreakdown[] }>({
    queryKey: ["weekly-load", weeks],
    queryFn: () => fetchAPI(`/training/weekly-load?weeks=${weeks}`),
    staleTime: 5 * 60 * 1000,
  });
}

export function useWeeklyGroupedActivities() {
  return useQuery<{ ok: boolean; groups: ActivityGroup[] }>({
    queryKey: ["activities-grouped"],
    queryFn: () => fetchAPI("/activities/weekly-grouped"),
    staleTime: 5 * 60 * 1000,
  });
}

export function usePredictionHistory(months: number = 6) {
  return useQuery<{ ok: boolean; series: PredictionHistoryPoint[] }>({
    queryKey: ["prediction-history", months],
    queryFn: () => fetchAPI(`/training/running/prediction-history?months=${months}`),
    staleTime: 10 * 60 * 1000,
  });
}
