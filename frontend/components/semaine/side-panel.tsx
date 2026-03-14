"use client";

import { useState } from "react";
import { useDraggable } from "@dnd-kit/core";
import { PanelRightClose, PanelRightOpen, Plus, Lightbulb } from "lucide-react";
import { toast } from "sonner";
import { AnimatePresence, motion } from "framer-motion";
import { useCreateTask } from "@/lib/queries/use-planner";
import { CATEGORY_COLORS, CATEGORY_LABELS, TRIAGE_LABELS } from "@/lib/constants";
import type { BoardTask, Category } from "@/lib/types";

interface SidePanelProps {
  tasks: BoardTask[];
  isOpen: boolean;
  onToggle: () => void;
}

export function SidePanel({ tasks, isOpen, onToggle }: SidePanelProps) {
  return (
    <div className="flex shrink-0">
      {/* Toggle button */}
      <button
        onClick={onToggle}
        className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-surface-2 transition-colors self-start mt-1"
      >
        {isOpen ? (
          <PanelRightClose className="h-4 w-4 text-text-muted" />
        ) : (
          <PanelRightOpen className="h-4 w-4 text-text-muted" />
        )}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 272, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="w-[272px] space-y-4">
              <BacklogSection tasks={tasks} />
              <IdeasSection />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Backlog ───────────────────────────────────────────────────

function BacklogSection({ tasks }: { tasks: BoardTask[] }) {
  return (
    <div className="glass rounded-xl p-3">
      <h3 className="mb-2 text-xs font-semibold text-text-secondary">
        Backlog{" "}
        <span className="font-normal text-text-muted">{tasks.length}</span>
      </h3>
      {tasks.length === 0 ? (
        <p className="text-[10px] text-text-muted">Aucune tâche.</p>
      ) : (
        <div className="space-y-1.5 max-h-[45vh] overflow-y-auto">
          {tasks.map((task) => (
            <BacklogCard key={task.id} task={task} />
          ))}
        </div>
      )}
    </div>
  );
}

function BacklogCard({ task }: { task: BoardTask }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: task.id,
    data: { task },
  });

  const color =
    CATEGORY_COLORS[task.category as Category] ?? "var(--color-autre)";

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      className={`cursor-grab rounded-lg bg-surface-0 px-2.5 py-2 transition-all ${
        isDragging ? "opacity-40 scale-95" : "hover:bg-surface-1"
      }`}
    >
      <div className="flex items-center gap-2">
        <span
          className="rounded px-1 py-0.5 text-[9px] font-medium uppercase"
          style={{
            background: `color-mix(in srgb, ${color} 20%, transparent)`,
            color,
          }}
        >
          {CATEGORY_LABELS[task.category as Category] ?? task.category}
        </span>
        <span className="flex-1 truncate text-xs text-text-primary">
          {task.title}
        </span>
      </div>
      <div className="mt-0.5 text-[9px] text-text-muted">
        {TRIAGE_LABELS[task.triage_status] ?? task.triage_status}
      </div>
    </div>
  );
}

// ── Ideas quick-capture ───────────────────────────────────────

function IdeasSection() {
  const createTask = useCreateTask();
  const [newIdea, setNewIdea] = useState("");

  const handleAdd = () => {
    if (!newIdea.trim()) return;
    createTask.mutate(
      {
        title: newIdea.trim(),
        category: "autre",
        triage_status: "a_determiner",
      },
      {
        onSuccess: () => {
          setNewIdea("");
          toast.success("Idée ajoutée");
        },
      },
    );
  };

  return (
    <div className="glass rounded-xl p-3">
      <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-text-secondary">
        <Lightbulb className="h-3 w-3 text-accent-yellow" />
        Idées
      </h3>
      <div className="flex gap-1.5">
        <input
          type="text"
          value={newIdea}
          onChange={(e) => setNewIdea(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
          placeholder="Nouvelle idée..."
          className="flex-1 rounded-lg bg-surface-0 px-2 py-1.5 text-xs text-text-primary placeholder-text-muted outline-none focus:ring-1 focus:ring-accent-yellow/50"
        />
        <button
          onClick={handleAdd}
          disabled={createTask.isPending}
          className="rounded-lg bg-accent-yellow/20 p-1.5 text-accent-yellow hover:bg-accent-yellow/30 transition-colors disabled:opacity-50"
        >
          <Plus className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
