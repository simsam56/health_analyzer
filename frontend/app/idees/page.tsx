"use client";

import { useState } from "react";
import { useBoardTasks, useCreateTask } from "@/lib/queries/use-planner";
import { Lightbulb, Plus } from "lucide-react";
import { toast } from "sonner";

const IDEA_CATEGORIES = ["Pro", "Perso", "Projet", "À creuser"] as const;

export default function IdeesPage() {
  const { data, isLoading } = useBoardTasks();
  const createTask = useCreateTask();
  const [newIdea, setNewIdea] = useState("");
  const [category, setCategory] = useState<string>("Pro");

  // Les idées sont des tâches "autre" avec triage "a_determiner"
  const ideas = data?.tasks?.filter(
    (t) => t.triage_status === "a_determiner"
  ) ?? [];

  const handleAdd = () => {
    if (!newIdea.trim()) return;
    createTask.mutate(
      {
        title: newIdea.trim(),
        category: "autre",
        triage_status: "a_determiner",
        notes: `Catégorie idée : ${category}`,
      },
      {
        onSuccess: () => {
          setNewIdea("");
          toast.success("Idée ajoutée !");
        },
      },
    );
  };

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent-yellow border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Formulaire d'ajout */}
      <div className="glass rounded-2xl p-5">
        <h3 className="mb-3 flex items-center gap-2 text-base font-semibold">
          <Lightbulb className="h-4 w-4 text-accent-yellow" />
          Capturer une idée
        </h3>
        <div className="flex gap-2">
          <input
            type="text"
            value={newIdea}
            onChange={(e) => setNewIdea(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAdd()}
            placeholder="Nouvelle idée..."
            className="flex-1 rounded-lg bg-surface-0 px-3 py-2 text-sm text-text-primary placeholder-text-muted outline-none focus:ring-1 focus:ring-accent-yellow/50"
          />
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="rounded-lg bg-surface-0 px-2 py-2 text-xs text-text-secondary outline-none"
          >
            {IDEA_CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <button
            onClick={handleAdd}
            disabled={createTask.isPending}
            className="flex items-center gap-1 rounded-lg bg-accent-yellow/20 px-3 py-2 text-sm font-medium text-accent-yellow hover:bg-accent-yellow/30 transition-colors disabled:opacity-50"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Liste des idées */}
      <div className="glass rounded-2xl p-5">
        <h3 className="mb-3 text-base font-semibold">
          Mes idées
          <span className="ml-2 text-sm font-normal text-text-muted">{ideas.length}</span>
        </h3>
        {ideas.length === 0 ? (
          <p className="text-text-muted text-sm">Aucune idée pour le moment. Commencez à capturer !</p>
        ) : (
          <div className="space-y-2">
            {ideas.map((t) => (
              <div key={t.id} className="flex items-center gap-3 rounded-lg bg-surface-0 px-3 py-2">
                <Lightbulb className="h-3.5 w-3.5 text-accent-yellow" />
                <span className="flex-1 text-sm">{t.title}</span>
                <span className="text-[10px] text-text-muted">
                  {new Date(t.created_at).toLocaleDateString("fr-FR", { day: "numeric", month: "short" })}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
