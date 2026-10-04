import type { PasteurisationPhaseEdit, PasteurisationPhaseSlot } from "@/lib/types";
import {
  STATUS_ACCENTS,
  STATUS_BADGES,
  STATUS_DOTS,
  STATUS_LABELS,
  type CheckpointStatus,
} from "@/lib/status";

export type PhaseState = CheckpointStatus;

export const PHASE_STATE_LABELS = STATUS_LABELS;
export const PHASE_STATE_BADGES = STATUS_BADGES;
export const PHASE_STATE_ACCENTS = STATUS_ACCENTS;
export const PHASE_STATE_DOTS = STATUS_DOTS;

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
