import type { PasteurisationPhaseEdit, PasteurisationPhaseSlot } from "@/lib/types";
import {
  STATUS_ACCENTS,
  STATUS_BADGES,
  STATUS_DOTS,
  type CheckpointStatus,
} from "@/lib/status";
import { t, type Locale } from "@/lib/i18n";

export type PhaseState = CheckpointStatus;

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
export function describePhaseChange(locale: Locale, entry: PasteurisationPhaseEdit): string {
  const parts: string[] = [];
  if (entry.previous_started_at !== entry.new_started_at) {
    parts.push(
      t(locale, "début {before} → {after}", {
        before: showTime(entry.previous_started_at),
        after: showTime(entry.new_started_at),
      }),
    );
  }
  if (entry.previous_ended_at !== entry.new_ended_at) {
    parts.push(
      t(locale, "fin {before} → {after}", {
        before: showTime(entry.previous_ended_at),
        after: showTime(entry.new_ended_at),
      }),
    );
  }
  const before = entry.previous_target_temperature_celsius;
  const after = entry.new_target_temperature_celsius;
  if (before !== after) {
    parts.push(
      t(locale, "cible {before} → {after}", {
        before: before === null ? "—" : `${before} °C`,
        after: after === null ? "—" : `${after} °C`,
      }),
    );
  }
  if (entry.previous_observation !== entry.new_observation) {
    parts.push(t(locale, "observation modifiée"));
  }
  return parts.length > 0 ? parts.join(" · ") : t(locale, "aucun changement");
}
