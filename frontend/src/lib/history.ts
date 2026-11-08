import type { ModuleKey } from "@/lib/modules";
import { t, type Locale } from "@/lib/i18n";
import type { HistoryAction, HistoryEntity } from "@/lib/types";

export function historyEntityLabel(locale: Locale, entity: HistoryEntity): string {
  switch (entity) {
    case "temperature_reading":
      return t(locale, "Relevé");
    case "cleaning_record":
      return t(locale, "Nettoyage");
    case "pasteurisation_phase":
      return t(locale, "Pasteurisation");
    case "transport":
      return t(locale, "Transport");
  }
}

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

export const HISTORY_ENTITY_MODULES: Record<HistoryEntity, ModuleKey> = {
  temperature_reading: "readings",
  cleaning_record: "cleaning",
  pasteurisation_phase: "pasteurisation",
  transport: "transport",
};

export function historyActionLabel(locale: Locale, action: HistoryAction): string {
  switch (action) {
    case "created":
      return t(locale, "Saisie");
    case "updated":
      return t(locale, "Correction");
    case "deleted":
      return t(locale, "Suppression");
  }
}

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
