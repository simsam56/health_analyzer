"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchAPI } from "@/lib/api";
import type { DashboardData } from "@/lib/types";

export function useDashboard() {
  return useQuery<DashboardData>({
    queryKey: ["dashboard"],
    queryFn: () => fetchAPI<DashboardData>("/dashboard"),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 60 * 1000, // refresh toutes les 60s
  });
}
