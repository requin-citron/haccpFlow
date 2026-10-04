import type { PasteurisationPhaseEdit, PasteurisationPhaseSlot } from "@/lib/types";

export type PhaseState = "complete" | "partial" | "empty";

export const PHASE_STATE_LABELS: Record<PhaseState, string> = {
  complete: "Complet",
  partial: "En cours",
  empty: "À remplir",
};

export const PHASE_STATE_BADGES: Record<PhaseState, string> = {
  complete: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  partial: "bg-amber-50 text-amber-700 ring-amber-200",
  empty: "bg-slate-100 text-slate-500 ring-slate-200",
};

export const PHASE_STATE_ACCENTS: Record<PhaseState, string> = {
  complete: "border-emerald-200",
  partial: "border-amber-200",
  empty: "border-slate-200",
};

export const PHASE_STATE_DOTS: Record<PhaseState, string> = {
  complete: "bg-emerald-500",
  partial: "bg-amber-500",
  empty: "bg-slate-300",
};

/** A phase is complete with both times and its target temperature. */
export function phaseState(slot: PasteurisationPhaseSlot): PhaseState {
  if (
    slot.started_at !== null &&
    slot.ended_at !== null &&
    slot.target_temperature_celsius !== null
  ) {
    return "complete";
  }
  const filled =
    slot.started_at !== null ||
    slot.ended_at !== null ||
    slot.target_temperature_celsius !== null ||
    slot.observation !== null;
  return filled ? "partial" : "empty";
}

function showTime(value: string | null): string {
  return value ? value.slice(0, 5) : "—";
}

/** Human summary of what a phase audit line changed. */
export function describePhaseChange(entry: PasteurisationPhaseEdit): string {
  const parts: string[] = [];
  if (entry.previous_started_at !== entry.new_started_at) {
    parts.push(
      `début ${showTime(entry.previous_started_at)} → ${showTime(entry.new_started_at)}`,
    );
  }
  if (entry.previous_ended_at !== entry.new_ended_at) {
    parts.push(`fin ${showTime(entry.previous_ended_at)} → ${showTime(entry.new_ended_at)}`);
  }
  const before = entry.previous_target_temperature_celsius;
  const after = entry.new_target_temperature_celsius;
  if (before !== after) {
    parts.push(
      `cible ${before === null ? "—" : `${before} °C`} → ${after === null ? "—" : `${after} °C`}`,
    );
  }
  if (entry.previous_observation !== entry.new_observation) {
    parts.push("observation modifiée");
  }
  return parts.length > 0 ? parts.join(" · ") : "aucun changement";
}
