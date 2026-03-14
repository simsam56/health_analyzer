"use client";

import { RefreshCw, CheckCircle2, AlertCircle, XCircle } from "lucide-react";

interface SyncStatusProps {
  appleConnected?: boolean;
  applePermission?: string;
  appleError?: string | null;
  isSyncing: boolean;
  onSync: () => void;
}

export function SyncStatus({
  appleConnected,
  applePermission,
  appleError,
  isSyncing,
  onSync,
}: SyncStatusProps) {
  let statusIcon: React.ReactNode;
  let statusText: string;
  let statusColor: string;

  if (appleConnected === undefined) {
    statusText = "Chargement...";
    statusColor = "text-text-muted";
    statusIcon = <RefreshCw className="h-3 w-3 animate-spin" />;
  } else if (appleError) {
    statusText = "Erreur";
    statusColor = "text-red-400";
    statusIcon = <XCircle className="h-3 w-3" />;
  } else if (!appleConnected || applePermission === "denied") {
    statusText = "D\u00e9connect\u00e9";
    statusColor = "text-amber-400";
    statusIcon = <AlertCircle className="h-3 w-3" />;
  } else {
    statusText = "Connect\u00e9";
    statusColor = "text-green-400";
    statusIcon = <CheckCircle2 className="h-3 w-3" />;
  }

  return (
    <div className="flex items-center gap-2">
      {/* Apple Calendar badge */}
      <div
        className={`flex items-center gap-1 rounded-lg bg-surface-0 px-2 py-1.5 text-[10px] font-medium ${statusColor}`}
      >
        {statusIcon}
        <span>Apple</span>
        <span className="text-text-muted">·</span>
        <span>{statusText}</span>
      </div>

      {/* Google Calendar placeholder */}
      <div className="flex items-center gap-1 rounded-lg bg-surface-0 px-2 py-1.5 text-[10px] font-medium text-text-muted">
        <AlertCircle className="h-3 w-3" />
        <span>Google</span>
        <span className="text-text-muted">·</span>
        <span>Non connect\u00e9</span>
      </div>

      {/* Sync button */}
      <button
        onClick={onSync}
        disabled={isSyncing}
        className="flex items-center gap-1 rounded-lg bg-surface-0 px-2 py-1.5 text-[10px] font-medium text-text-secondary hover:bg-surface-1 hover:text-text-primary disabled:opacity-50"
        title="Synchroniser les calendriers"
      >
        <RefreshCw
          className={`h-3 w-3 ${isSyncing ? "animate-spin" : ""}`}
        />
        Sync
      </button>
    </div>
  );
}
