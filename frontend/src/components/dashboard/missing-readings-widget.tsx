import { ClipboardIcon } from "@/components/icons";
import { t, type Locale } from "@/lib/i18n";
import type { DashboardMissingReadings } from "@/lib/types";

export function MissingReadingsWidget({
  readings,
  locale,
}: {
  readings: DashboardMissingReadings;
  locale: Locale;
}) {
  const complete = readings.missing_slots === 0;

  return (
    <section className="flex h-full min-h-0 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <header className="flex shrink-0 items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span
            className={`grid size-11 shrink-0 place-items-center rounded-xl ring-1 ${
              complete
                ? "bg-emerald-50 text-emerald-700 ring-emerald-100"
                : "bg-amber-50 text-amber-700 ring-amber-100"
            }`}
          >
            <ClipboardIcon className="size-5" />
          </span>
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              {t(locale, "Relevés manquants")}
            </h2>
          </div>
        </div>
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-600">
          {t(locale, "{filled} / {total} saisis", {
            filled: readings.filled_slots,
            total: readings.total_slots,
          })}
        </span>
      </header>

      <div className="mt-5 flex min-h-0 flex-1 flex-col justify-center">
        <div className="flex items-end gap-3">
          <p
            className={`text-4xl font-semibold tracking-tight tabular-nums ${
              complete ? "text-emerald-700" : "text-amber-700"
            }`}
          >
            {readings.missing_slots}
          </p>
          <p className="pb-1 text-sm text-slate-500">
            {t(locale, "créneaux à compléter")}
          </p>
        </div>
      </div>
    </section>
  );
}
