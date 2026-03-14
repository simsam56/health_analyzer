"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchAPI, mutateAPI } from "@/lib/api";
import type { BoardTask, PlannerEvent } from "@/lib/types";

export function usePlannerEvents(start?: string, end?: string) {
  const params = new URLSearchParams();
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  const qs = params.toString();

  return useQuery<{ ok: boolean; events: PlannerEvent[] }>({
    queryKey: ["planner-events", start, end],
    queryFn: () => fetchAPI(`/planner/events${qs ? `?${qs}` : ""}`),
    staleTime: 10 * 1000,
    refetchInterval: 30 * 1000,
  });
}

export function useBoardTasks() {
  return useQuery<{ ok: boolean; tasks: BoardTask[] }>({
    queryKey: ["board-tasks"],
    queryFn: () => fetchAPI("/planner/board"),
    staleTime: 10 * 1000,
    refetchInterval: 30 * 1000,
  });
}

export function useCreateTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      mutateAPI("/planner/tasks", "POST", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["planner-events"] });
      qc.invalidateQueries({ queryKey: ["board-tasks"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useUpdateTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: number } & Record<string, unknown>) =>
      mutateAPI(`/planner/tasks/${id}`, "PATCH", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["planner-events"] });
      qc.invalidateQueries({ queryKey: ["board-tasks"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useDeleteTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => mutateAPI(`/planner/tasks/${id}`, "DELETE"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["planner-events"] });
      qc.invalidateQueries({ queryKey: ["board-tasks"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useSyncCalendar() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => mutateAPI("/planner/calendar/sync", "POST"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["planner-events"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["calendar-status"] });
    },
  });
}

export function useCalendarStatus() {
  return useQuery<{
    ok: boolean;
    permission: string;
    error: string | null;
    calendars_count: number;
    default_calendar: string | null;
  }>({
    queryKey: ["calendar-status"],
    queryFn: () => fetchAPI("/planner/calendar/status"),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useScheduleTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      start_at,
      end_at,
    }: {
      id: number;
      start_at: string;
      end_at: string;
    }) =>
      mutateAPI(`/planner/tasks/${id}`, "PATCH", {
        start_at,
        end_at,
        scheduled: true,
        triage_status: "a_planifier",
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["planner-events"] });
      qc.invalidateQueries({ queryKey: ["board-tasks"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
