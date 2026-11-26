import {
  addDays,
  daysBetween,
  formatDayLabel,
  formatShortDay,
  isIsoDate,
  todayIso,
} from "@/lib/format";
import type { Locale, MessageKey } from "@/lib/i18n";

export type DashboardRange = {
  from: string;
  to: string;
};

export type DashboardPreset =
  | "today"
  | "yesterday"
  | "last_7_days"
  | "last_30_days"
  | "this_month"
  | "previous_month"
  | "this_year";

export type DashboardPresetOption = {
  value: DashboardPreset;
  labelKey: MessageKey;
};

export const DASHBOARD_PRESETS: readonly DashboardPresetOption[] = [
  { value: "today", labelKey: "Aujourd'hui" },
  { value: "yesterday", labelKey: "Hier" },
  { value: "last_7_days", labelKey: "7 derniers jours" },
  { value: "last_30_days", labelKey: "30 derniers jours" },
  { value: "this_month", labelKey: "Ce mois-ci" },
  { value: "previous_month", labelKey: "Mois précédent" },
  { value: "this_year", labelKey: "Année courante" },
];

function firstDayOfMonth(isoDate: string): string {
  return `${isoDate.slice(0, 7)}-01`;
}

function previousMonthStart(isoDate: string): string {
  const date = new Date(`${firstDayOfMonth(isoDate)}T12:00:00Z`);
  date.setUTCMonth(date.getUTCMonth() - 1);
  return date.toISOString().slice(0, 10);
}

function lastDayOfPreviousMonth(isoDate: string): string {
  return addDays(firstDayOfMonth(isoDate), -1);
}

export function dashboardPresetRange(
  preset: DashboardPreset,
  today = todayIso(),
): DashboardRange {
  switch (preset) {
    case "today":
      return { from: today, to: today };
    case "yesterday": {
      const yesterday = addDays(today, -1);
      return { from: yesterday, to: yesterday };
    }
    case "last_7_days":
      return { from: addDays(today, -6), to: today };
    case "last_30_days":
      return { from: addDays(today, -29), to: today };
    case "this_month":
      return { from: firstDayOfMonth(today), to: today };
    case "previous_month":
      return {
        from: previousMonthStart(today),
        to: lastDayOfPreviousMonth(today),
      };
    case "this_year":
      return {
        from: `${today.slice(0, 4)}-01-01`,
        to: today,
      };
  }
}

export function resolveDashboardRange(
  params: { from?: string; to?: string },
  today = todayIso(),
): DashboardRange {
  const from = isIsoDate(params.from?.trim()) ? params.from.trim() : today;
  const to = isIsoDate(params.to?.trim()) ? params.to.trim() : today;
  if (daysBetween(from, to) < 0) {
    return { from: today, to: today };
  }
  return { from, to };
}

export function sameDashboardRange(
  first: DashboardRange,
  second: DashboardRange,
): boolean {
  return first.from === second.from && first.to === second.to;
}

export function dashboardRangeLabel(
  locale: Locale,
  range: DashboardRange,
): string {
  if (range.from === range.to) {
    return formatDayLabel(locale, range.from);
  }
  return `${formatShortDay(locale, range.from)} → ${formatShortDay(locale, range.to)}`;
}
