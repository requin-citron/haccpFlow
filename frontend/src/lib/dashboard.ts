import {
  addDays,
  daysBetween,
  formatDayLabel,
  formatShortDay,
  isIsoDate,
  todayIso,
} from "@/lib/format";
import { formatLocale, type Locale, type MessageKey } from "@/lib/i18n";

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
  | "previous_month";

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

export type TimelineTick = {
  key: string;
  label: string;
};

function monthTickLabel(locale: Locale, isoDate: string): string {
  return new Intl.DateTimeFormat(formatLocale(locale), {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${isoDate}T12:00:00Z`));
}

function monthlyStarts(from: string, to: string): string[] {
  const dates: string[] = [];
  const cursor = new Date(`${firstDayOfMonth(from)}T12:00:00Z`);
  const end = Date.parse(`${to}T12:00:00Z`);

  while (cursor.getTime() <= end) {
    const isoDate = cursor.toISOString().slice(0, 10);
    if (isoDate >= from) {
      dates.push(isoDate);
    }
    cursor.setUTCMonth(cursor.getUTCMonth() + 1);
  }
  return dates;
}

export function buildTimelineTicks(
  range: DashboardRange,
  locale: Locale,
): TimelineTick[] {
  const days = daysBetween(range.from, range.to);

  if (days === 0) {
    return ["00:00", "06:00", "12:00", "18:00", "24:00"].map((label) => ({
      key: label,
      label,
    }));
  }

  if (days <= 14) {
    return Array.from({ length: days + 1 }, (_, index) => {
      const isoDate = addDays(range.from, index);
      return { key: isoDate, label: formatShortDay(locale, isoDate) };
    });
  }

  if (days <= 90) {
    const dates: string[] = [];
    for (let offset = 0; offset <= days; offset += 7) {
      dates.push(addDays(range.from, offset));
    }
    if (dates.at(-1) !== range.to) {
      dates.push(range.to);
    }
    return dates.map((isoDate) => ({
      key: isoDate,
      label: formatShortDay(locale, isoDate),
    }));
  }

  const dates = [range.from, ...monthlyStarts(range.from, range.to)];
  if (dates.at(-1) !== range.to) {
    dates.push(range.to);
  }
  return [...new Set(dates)].map((isoDate) => ({
    key: isoDate,
    label: isoDate === range.from || isoDate === range.to
      ? formatShortDay(locale, isoDate)
      : monthTickLabel(locale, isoDate),
  }));
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
