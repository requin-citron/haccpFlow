import type { HistoryAction, HistoryEntity } from "@/lib/types";

export const HISTORY_ENTITY_LABELS: Record<HistoryEntity, string> = {
  temperature_reading: "Relevé",
  cleaning_record: "Nettoyage",
  pasteurisation_phase: "Pasteurisation",
  transport: "Transport",
};

export const HISTORY_ENTITY_TONES: Record<HistoryEntity, string> = {
  temperature_reading: "bg-sky-50 text-sky-700 ring-sky-200",
  cleaning_record: "bg-teal-50 text-teal-700 ring-teal-200",
  pasteurisation_phase: "bg-orange-50 text-orange-700 ring-orange-200",
  transport: "bg-indigo-50 text-indigo-700 ring-indigo-200",
};

/**
 * Route prefix of the entity an entry belongs to, or null when no screen
 * exists yet: the feed then renders the subject as plain text.
 */
export const HISTORY_ENTITY_LINKS: Record<HistoryEntity, string | null> = {
  temperature_reading: "/equipment",
  cleaning_record: "/cleaning",
  pasteurisation_phase: "/pasteurisation",
  transport: "/transport",
};

export const HISTORY_ACTION_LABELS: Record<HistoryAction, string> = {
  created: "Saisie",
  updated: "Correction",
  deleted: "Suppression",
};

export const HISTORY_ACTION_TONES: Record<HistoryAction, string> = {
  created: "text-emerald-700",
  updated: "text-amber-700",
  deleted: "text-rose-700",
};

export function historyEntryLink(entry: {
  entity: HistoryEntity;
  target_id: string;
}): string | null {
  const prefix = HISTORY_ENTITY_LINKS[entry.entity];
  return prefix === null ? null : `${prefix}/${entry.target_id}`;
}
