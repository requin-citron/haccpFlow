import { DashboardIcon } from "@/components/icons";
import {
  buildTimelineTicks,
  dashboardRangeLabel,
  type DashboardRange,
} from "@/lib/dashboard";
import { t, type Locale } from "@/lib/i18n";

export function DashboardTimeline({
  range,
  locale,
}: {
  range: DashboardRange;
  locale: Locale;
}) {
  const ticks = buildTimelineTicks(range, locale);
  const gridTemplateColumns = `repeat(${ticks.length}, minmax(5.5rem, 1fr))`;
  const minimumWidth = Math.max(560, ticks.length * 88);

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
        <div>
          <h2 className="text-base font-semibold text-slate-900">{t(locale, "Timeline")}</h2>
          <p className="mt-0.5 text-xs capitalize text-slate-500">
            {dashboardRangeLabel(locale, range)} · UTC
          </p>
        </div>
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-600">
          {t(locale, "Axe temporel")}
        </span>
      </header>

      <div className="overflow-x-auto">
        <div className="p-4" style={{ minWidth: `${minimumWidth}px` }}>
          <div
            className="grid border-b border-slate-200"
            style={{ gridTemplateColumns }}
            aria-label={t(locale, "Graduations de la timeline")}
          >
            {ticks.map((tick) => (
              <div
                key={tick.key}
                className="relative min-h-10 border-l border-slate-200 pl-2 text-[11px] font-medium tabular-nums text-slate-500 first:border-l-0"
              >
                <span className="whitespace-nowrap">{tick.label}</span>
                <span className="absolute bottom-0 left-0 h-1.5 w-px bg-slate-300" />
              </div>
            ))}
          </div>

          <div
            className="relative grid min-h-[26rem]"
            style={{ gridTemplateColumns }}
            aria-label={t(locale, "Zone des futurs widgets")}
          >
            {ticks.map((tick) => (
              <div key={tick.key} className="border-l border-dashed border-slate-100 first:border-l-0" />
            ))}
            <div className="pointer-events-none absolute inset-0 grid place-items-center p-6">
              <div className="max-w-sm rounded-2xl border border-dashed border-slate-300 bg-slate-50/95 px-6 py-8 text-center shadow-sm">
                <span className="mx-auto grid size-11 place-items-center rounded-xl bg-white text-slate-400 ring-1 ring-slate-200">
                  <DashboardIcon className="size-5" />
                </span>
                <h3 className="mt-3 text-sm font-semibold text-slate-800">
                  {t(locale, "Aucun widget configuré")}
                </h3>
                <p className="mt-1 text-xs text-slate-500">
                  {t(
                    locale,
                    "Les futurs widgets utiliseront cette période et cet axe temporel.",
                  )}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
