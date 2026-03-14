"use client";

interface LoadingSpinnerProps {
  color?: string;
}

export function LoadingSpinner({ color = "border-accent-blue" }: LoadingSpinnerProps) {
  return (
    <div className="flex h-64 items-center justify-center">
      <div className={`h-8 w-8 animate-spin rounded-full border-2 ${color} border-t-transparent`} />
    </div>
  );
}
