"use client";

import { Lightbulb, ListTodo } from "lucide-react";

interface SidePanelProps {
  activeTab: "ideas" | "backlog";
  onTabChange: (tab: "ideas" | "backlog") => void;
  children: React.ReactNode;
}

export function SidePanel({ activeTab, onTabChange, children }: SidePanelProps) {
  return (
    <div className="glass flex h-full flex-col overflow-hidden rounded-2xl">
      {/* Tab switcher */}
      <div className="flex border-b border-white/[0.06]">
        <button
          onClick={() => onTabChange("ideas")}
          className={`flex flex-1 items-center justify-center gap-1.5 py-2.5 text-xs font-medium transition-colors ${
            activeTab === "ideas"
              ? "border-b-2 border-accent-yellow text-accent-yellow"
              : "text-text-muted hover:text-text-secondary"
          }`}
        >
          <Lightbulb className="h-3.5 w-3.5" />
          Id\u00e9es
        </button>
        <button
          onClick={() => onTabChange("backlog")}
          className={`flex flex-1 items-center justify-center gap-1.5 py-2.5 text-xs font-medium transition-colors ${
            activeTab === "backlog"
              ? "border-b-2 border-accent-blue text-accent-blue"
              : "text-text-muted hover:text-text-secondary"
          }`}
        >
          <ListTodo className="h-3.5 w-3.5" />
          Backlog
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3">{children}</div>
    </div>
  );
}
