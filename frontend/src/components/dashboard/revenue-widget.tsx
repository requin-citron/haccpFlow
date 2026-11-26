import { BanknoteIcon } from "@/components/icons";
import { formatEuros } from "@/lib/format";
import { t, type Locale } from "@/lib/i18n";
import type { DashboardRevenue } from "@/lib/types";

function BreakdownCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: string;
}) {
  return (
    <div className="min-w-0 rounded-lg bg-slate-50 px-2 py-2">
      <p className="text-[10px] font-medium leading-4 text-slate-500">
        {label}
      </p>
      <p className={`mt-0.5 truncate text-sm font-semibold tabular-nums ${tone}`}>
        {value}
      </p>
    </div>
  );
}

export function RevenueWidget({
  revenue,
  locale,
}: {
  revenue: DashboardRevenue;
  locale: Locale;
}) {
  return (
    <section className="revenue-widget flex h-full min-h-0 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <header className="flex shrink-0 flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100">
            <BanknoteIcon className="size-5" />
          </span>
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              {t(locale, "Chiffre d'affaires")}
            </h2>
            <p className="mt-0.5 text-xs text-slate-500">
              {t(
                locale,
                "Toutes les caisses clôturées sur la période sélectionnée.",
              )}
            </p>
          </div>
        </div>
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-600">
          {t(locale, "Suivis clôturés : {count}", {
            count: revenue.closed_session_count,
          })}
        </span>
      </header>

      <div className="mt-4 flex min-h-0 flex-1 flex-col justify-between gap-4">
        <div className="shrink-0">
          <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
            {t(locale, "Total encaissé")}
          </p>
          <p className="mt-1 text-3xl font-semibold tracking-tight tabular-nums text-slate-950">
            {formatEuros(locale, revenue.total_cents)}
          </p>
        </div>

        <div className="revenue-widget-breakdown grid min-h-0 gap-1.5">
          <BreakdownCard
            label={t(locale, "Espèces")}
            value={formatEuros(locale, revenue.cash_cents)}
            tone="text-emerald-800"
          />
          <BreakdownCard
            label={t(locale, "Chèques")}
            value={formatEuros(locale, revenue.cheque_cents)}
            tone="text-indigo-800"
          />
          <BreakdownCard
            label={t(locale, "Cartes bancaires")}
            value={formatEuros(locale, revenue.card_cents)}
            tone="text-sky-800"
          />
        </div>
      </div>

      {revenue.closed_session_count === 0 ? (
        <p className="mt-4 rounded-xl border border-dashed border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs text-slate-500">
          {t(locale, "Aucun suivi clôturé ne correspond à cette période.")}
        </p>
      ) : null}
    </section>
  );
}
