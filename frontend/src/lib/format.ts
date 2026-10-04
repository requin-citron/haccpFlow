import type {
  CleaningFrequency,
  CleaningStatus,
  EquipmentType,
  PasteurisationPhase,
  ReadingSlot,
  ReadingSource,
} from "@/lib/types";

export const EQUIPMENT_TYPE_LABELS: Record<EquipmentType, string> = {
  fridge: "Réfrigérateur",
  freezer: "Congélateur",
};

export const SLOT_LABELS: Record<ReadingSlot, string> = {
  morning: "Matin",
  evening: "Soir",
};

export const SOURCE_LABELS: Record<ReadingSource, string> = {
  manual: "Manuel",
  sensor: "Capteur",
};

export const CLEANING_FREQUENCY_LABELS: Record<CleaningFrequency, string> = {
  after_each_use: "Après chaque usage",
  daily: "Quotidien",
  weekly: "Hebdomadaire",
};

export const CLEANING_STATUS_LABELS: Record<CleaningStatus, string> = {
  overdue: "En retard",
  due_today: "À faire aujourd'hui",
  upcoming: "À venir",
};

export const PASTEURISATION_PHASE_LABELS: Record<PasteurisationPhase, string> = {
  preheating: "Préchauffage",
  holding: "Palier (pasteurisation)",
  cooling: "Refroidissement",
};

export const PASTEURISATION_PHASE_SHORT_LABELS: Record<PasteurisationPhase, string> = {
  preheating: "Pré",
  holding: "Pal",
  cooling: "Ref",
};

const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

export function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function isIsoDate(value: string | undefined): value is string {
  if (!value || !DATE_PATTERN.test(value)) {
    return false;
  }
  return !Number.isNaN(new Date(`${value}T12:00:00Z`).getTime());
}

export function addDays(isoDate: string, days: number): string {
  const date = new Date(`${isoDate}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

export function daysBetween(fromIso: string, toIso: string): number {
  const from = Date.parse(`${fromIso}T12:00:00Z`);
  const to = Date.parse(`${toIso}T12:00:00Z`);
  return Math.round((to - from) / 86_400_000);
}

export function formatRelativeDue(nextDue: string, today: string): string {
  const days = daysBetween(today, nextDue);
  if (days === 0) {
    return "aujourd'hui";
  }
  if (days === 1) {
    return "demain";
  }
  if (days === -1) {
    return "hier";
  }
  return days < 0 ? `il y a ${-days} jours` : `dans ${days} jours`;
}

export function formatDayLabel(isoDate: string): string {
  return new Intl.DateTimeFormat("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${isoDate}T12:00:00Z`));
}

export function formatShortDay(isoDate: string): string {
  return new Intl.DateTimeFormat("fr-FR", {
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
    timeZone: "UTC",
  }).format(new Date(`${isoDate}T12:00:00Z`));
}

export function formatDateTimeUtc(isoDateTime: string): string {
  const formatted = new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  }).format(new Date(isoDateTime));
  return `${formatted} UTC`;
}

/** UTC calendar day of an ISO datetime, for grouping a feed. */
export function dayFromIso(isoDateTime: string): string {
  return isoDateTime.slice(0, 10);
}

export function timeFromIso(isoDateTime: string): string {
  return isoDateTime.slice(11, 16);
}

/** "09:00:00" -> "09:00", for a time input. */
export function formatTimeInput(value: string | null): string {
  return value ? value.slice(0, 5) : "";
}

export function formatDuration(minutes: number | null): string {
  if (minutes === null) {
    return "—";
  }
  if (minutes < 60) {
    return `${minutes} min`;
  }
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest === 0 ? `${hours} h` : `${hours} h ${String(rest).padStart(2, "0")}`;
}

export function formatTemperature(value: number): string {
  const rounded = Math.round(value * 100) / 100;
  const text = Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
  return `${text.replace("-", "\u2212")} °C`;
}

export function formatTemperatureRange(min: number, max: number): string {
  return `${formatTemperature(min)} → ${formatTemperature(max)}`;
}

export function formatDate(isoDate: string): string {
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(isoDate));
}
