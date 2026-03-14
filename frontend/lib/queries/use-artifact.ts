"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchAPI } from "@/lib/api";
import type { ArtifactData } from "@/lib/types";

export function useArtifact() {
  return useQuery<ArtifactData>({
    queryKey: ["artifact"],
    queryFn: () => fetchAPI<ArtifactData>("/artifact"),
    staleTime: 2 * 60 * 1000, // 2 minutes
    refetchInterval: 60 * 1000, // refresh every 60s
  });
}
