import type {
  CleaningFrequency,
  CleaningStatus,
  EquipmentType,
  PasteurisationPhase,
  ReadingSlot,
  ReadingSource,
} from "@/lib/types";
import { formatLocale, t, type Locale } from "@/lib/i18n";

export function equipmentTypeLabel(locale: Locale, type: EquipmentType): string {
  return t(locale, type === "fridge" ? "Réfrigérateur" : "Congélateur");
}

export function readingSlotLabel(locale: Locale, slot: ReadingSlot): string {
  return t(locale, slot === "morning" ? "Matin" : "Soir");
}

export function readingSourceLabel(locale: Locale, source: ReadingSource): string {
  return t(locale, source === "manual" ? "Manuel" : "Capteur");
}

export function cleaningFrequencyLabel(
  locale: Locale,
  frequency: CleaningFrequency,
): string {
  switch (frequency) {
    case "after_each_use":
      return t(locale, "Après chaque usage");
    case "daily":
      return t(locale, "Quotidien");
    case "weekly":
      return t(locale, "Hebdomadaire");
  }
}

export function cleaningStatusLabel(locale: Locale, status: CleaningStatus): string {
  switch (status) {
    case "overdue":
      return t(locale, "En retard");
    case "due_today":
      return t(locale, "À faire aujourd'hui");
    case "upcoming":
      return t(locale, "À venir");
  }
}

export function pasteurisationPhaseLabel(
  locale: Locale,
  phase: PasteurisationPhase,
): string {
  switch (phase) {
    case "preheating":
      return t(locale, "Préchauffage");
    case "holding":
      return t(locale, "Palier (pasteurisation)");
    case "cooling":
      return t(locale, "Refroidissement");
  }
}

export function pasteurisationPhaseShortLabel(
  locale: Locale,
  phase: PasteurisationPhase,
): string {
  switch (phase) {
    case "preheating":
      return t(locale, "Pré");
    case "holding":
      return t(locale, "Pal");
    case "cooling":
      return t(locale, "Ref");
  }
}

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

export function formatRelativeDue(locale: Locale, nextDue: string, today: string): string {
  const days = daysBetween(today, nextDue);
  if (days === 0) {
    return t(locale, "aujourd'hui");
  }
  if (days === 1) {
    return t(locale, "demain");
  }
  if (days === -1) {
    return t(locale, "hier");
  }
  return days < 0
    ? t(locale, "il y a {days} jours", { days: -days })
    : t(locale, "dans {days} jours", { days });
}

export function formatDayLabel(locale: Locale, isoDate: string): string {
  return new Intl.DateTimeFormat(formatLocale(locale), {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${isoDate}T12:00:00Z`));
}

export function formatShortDay(locale: Locale, isoDate: string): string {
  return new Intl.DateTimeFormat(formatLocale(locale), {
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
    timeZone: "UTC",
  }).format(new Date(`${isoDate}T12:00:00Z`));
}

export function formatDateTimeUtc(locale: Locale, isoDateTime: string): string {
  const formatted = new Intl.DateTimeFormat(formatLocale(locale), {
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

export function formatDuration(locale: Locale, minutes: number | null): string {
  if (minutes === null) {
    return "—";
  }
  if (minutes < 60) {
    return t(locale, "{count} min", { count: minutes });
  }
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest === 0
    ? t(locale, "{hours} h", { hours })
    : t(locale, "{hours} h {minutes}", { hours, minutes: String(rest).padStart(2, "0") });
}

/** Cents to the active locale's euro display, e.g. 8228 -> "82,28 €". */
export function formatEuros(locale: Locale, cents: number): string {
  return new Intl.NumberFormat(formatLocale(locale), {
    style: "currency",
    currency: "EUR",
  }).format(cents / 100);
}

export function formatTemperature(locale: Locale, value: number): string {
  const text = new Intl.NumberFormat(formatLocale(locale), {
    maximumFractionDigits: 2,
  }).format(value);
  return `${text.replace("-", "\u2212")} °C`;
}

export function formatTemperatureRange(
  locale: Locale,
  min: number,
  max: number,
): string {
  return `${formatTemperature(locale, min)} → ${formatTemperature(locale, max)}`;
}

export function formatDate(locale: Locale, isoDate: string): string {
  return new Intl.DateTimeFormat(formatLocale(locale), {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(isoDate));
}

/** Human-readable file size, using binary units (Kio/Mio). */
export function formatFileSize(locale: Locale, bytes: number): string {
  const number = new Intl.NumberFormat(formatLocale(locale), {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
  if (bytes < 1024) {
    return `${bytes} ${t(locale, "o")}`;
  }
  if (bytes < 1024 * 1024) {
    return `${number.format(bytes / 1024)} ${t(locale, "Kio")}`;
  }
  return `${number.format(bytes / (1024 * 1024))} ${t(locale, "Mio")}`;
}
