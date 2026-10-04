import type { HistoryAction, HistoryEntity } from "@/lib/types";

export const HISTORY_ENTITY_LABELS: Record<HistoryEntity, string> = {
  temperature_reading: "Relevé",
  cleaning_record: "Nettoyage",
  pasteurisation_phase: "Pasteurisation",
};

export const HISTORY_ENTITY_TONES: Record<HistoryEntity, string> = {
  temperature_reading: "bg-sky-50 text-sky-700 ring-sky-200",
  cleaning_record: "bg-teal-50 text-teal-700 ring-teal-200",
  pasteurisation_phase: "bg-orange-50 text-orange-700 ring-orange-200",
};

/** Route prefix of the entity an entry belongs to. */
export const HISTORY_ENTITY_LINKS: Record<HistoryEntity, string> = {
  temperature_reading: "/equipment",
  cleaning_record: "/cleaning",
  pasteurisation_phase: "/pasteurisation",
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
}): string {
  return `${HISTORY_ENTITY_LINKS[entry.entity]}/${entry.target_id}`;
}
