import type { EquipmentType, ReadingSlot, ReadingSource } from "@/lib/types";

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
