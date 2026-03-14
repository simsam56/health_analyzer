"use client";

import clsx from "clsx";

type SkeletonVariant = "pills" | "chart" | "map";

interface SectionSkeletonProps {
  variant: SkeletonVariant;
}

export function SectionSkeleton({ variant }: SectionSkeletonProps) {
  if (variant === "pills") {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="glass h-24 animate-pulse rounded-xl" />
        ))}
      </div>
    );
  }

  if (variant === "map") {
    return (
      <div className="glass h-72 animate-pulse rounded-2xl" />
    );
  }

  return (
    <div className="glass h-52 animate-pulse rounded-2xl" />
  );
}
