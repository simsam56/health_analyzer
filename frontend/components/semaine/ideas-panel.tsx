"use client";

import { useState } from "react";
import type { BoardTask } from "@/lib/types";
import { IDEA_CATEGORIES } from "@/lib/constants";
import { IdeaCard } from "./idea-card";
import { Lightbulb, Plus } from "lucide-react";

interface IdeasPanelProps {
  ideas: BoardTask[];
  onCreateIdea: (title: string, category: string) => void;
  isCreating?: boolean;
}

export function IdeasPanel({ ideas, onCreateIdea, isCreating }: IdeasPanelProps) {
  const [newIdea, setNewIdea] = useState("");
  const [category, setCategory] = useState<string>("Pro");

  const handleAdd = () => {
    if (!newIdea.trim()) return;
    onCreateIdea(newIdea.trim(), category);
    setNewIdea("");
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Capture input */}
      <div>
        <h4 className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-text-primary">
          <Lightbulb className="h-3.5 w-3.5 text-accent-yellow" />
          Capturer une id\u00e9e
        </h4>
        <div className="flex gap-1.5">
          <input
            type="text"
            value={newIdea}
            onChange={(e) => setNewIdea(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAdd()}
            placeholder="Nouvelle id\u00e9e..."
            className="flex-1 rounded-lg bg-surface-0 px-2 py-1.5 text-xs text-text-primary placeholder-text-muted outline-none focus:ring-1 focus:ring-accent-yellow/50"
          />
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="rounded-lg bg-surface-0 px-1.5 py-1.5 text-[10px] text-text-secondary outline-none"
          >
            {IDEA_CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <button
            onClick={handleAdd}
            disabled={isCreating}
            className="flex items-center rounded-lg bg-accent-yellow/20 px-2 py-1.5 text-accent-yellow hover:bg-accent-yellow/30 disabled:opacity-50"
          >
            <Plus className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Ideas list */}
      <div className="space-y-1">
        <h4 className="text-[10px] font-medium uppercase text-text-muted">
          Mes id\u00e9es ({ideas.length})
        </h4>
        {ideas.length === 0 ? (
          <p className="py-3 text-center text-xs text-text-muted">
            Aucune id\u00e9e. Tapez ci-dessus pour capturer.
          </p>
        ) : (
          <div className="space-y-1">
            {ideas.map((idea) => (
              <IdeaCard key={idea.id} task={idea} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
