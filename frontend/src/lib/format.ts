import type { EquipmentType } from "@/lib/types";

export const EQUIPMENT_TYPE_LABELS: Record<EquipmentType, string> = {
  fridge: "Réfrigérateur",
  freezer: "Congélateur",
};

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
