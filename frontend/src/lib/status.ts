/** Shared "how filled is this block" states, used by phases and checkpoints. */

export type CheckpointStatus = "complete" | "partial" | "empty";

export const STATUS_LABELS: Record<CheckpointStatus, string> = {
  complete: "Complet",
  partial: "En cours",
  empty: "À remplir",
};

export const STATUS_BADGES: Record<CheckpointStatus, string> = {
  complete: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  partial: "bg-amber-50 text-amber-700 ring-amber-200",
  empty: "bg-slate-100 text-slate-500 ring-slate-200",
};

export const STATUS_ACCENTS: Record<CheckpointStatus, string> = {
  complete: "border-emerald-200",
  partial: "border-amber-200",
  empty: "border-slate-200",
};

export const STATUS_DOTS: Record<CheckpointStatus, string> = {
  complete: "bg-emerald-500",
  partial: "bg-amber-500",
  empty: "bg-slate-300",
};
