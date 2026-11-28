import { CheckIcon, DropletIcon } from "@/components/icons";
import { t, type Locale } from "@/lib/i18n";
import type { DashboardOverdueCleanings } from "@/lib/types";

export function OverdueCleaningsWidget({
  cleanings,
  locale,
}: {
  cleanings: DashboardOverdueCleanings;
  locale: Locale;
}) {
  const complete = cleanings.count === 0;

  return (
    <section className="flex h-full min-h-0 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <header className="flex shrink-0 items-start gap-3">
        <span
          className={`grid size-11 shrink-0 place-items-center rounded-xl ring-1 ${
            complete
              ? "bg-emerald-50 text-emerald-700 ring-emerald-100"
              : "bg-rose-50 text-rose-700 ring-rose-100"
          }`}
        >
          <DropletIcon className="size-5" />
        </span>
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-slate-900">
            {t(locale, "Nettoyages en retard")}
          </h2>
          <p className="mt-0.5 text-xs text-slate-500">
            {t(
              locale,
              "État actuel, non affecté par la période sélectionnée.",
            )}
          </p>
        </div>
      </header>

      <div className="mt-4 flex min-h-0 flex-1 items-end gap-3">
        <p
          className={`text-4xl font-semibold tracking-tight tabular-nums ${
            complete ? "text-emerald-700" : "text-rose-700"
          }`}
        >
          {cleanings.count}
        </p>
        <p className="pb-1 text-sm text-slate-500">
          {t(locale, "plans en retard")}
        </p>
        {complete ? (
          <CheckIcon className="mb-1.5 ml-auto size-5 text-emerald-600" />
        ) : null}
      </div>
    </section>
  );
}
