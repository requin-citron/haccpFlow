import { BanknoteIcon } from "@/components/icons";
import { formatEuros } from "@/lib/format";
import { t, type Locale } from "@/lib/i18n";
import type { DashboardRevenue } from "@/lib/types";

function BreakdownRow({
  label,
  value,
  dotClassName,
}: {
  label: string;
  value: string;
  dotClassName: string;
}) {
  return (
    <li className="flex min-w-0 items-center justify-between gap-3 py-2">
      <span className="flex min-w-0 items-center gap-2 text-xs font-medium text-slate-600">
        <span className={`size-2 shrink-0 rounded-full ${dotClassName}`} />
        <span className="truncate">{label}</span>
      </span>
      <span className="shrink-0 text-sm font-semibold tabular-nums text-slate-900">
        {value}
      </span>
    </li>
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
    <section className="relative flex h-full min-h-0 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <header className="flex shrink-0 items-start gap-3 pr-28">
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
      </header>

      <span className="absolute right-4 top-4 inline-flex min-h-6 items-center justify-center whitespace-nowrap rounded-full bg-slate-100 px-2.5 py-1 text-center text-[11px] font-medium leading-none text-slate-600">
        {t(locale, "Suivis clôturés : {count}", {
          count: revenue.closed_session_count,
        })}
      </span>

      <div className="mt-4 flex min-h-0 flex-1 flex-col justify-between gap-4">
        <div className="shrink-0">
          <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
            {t(locale, "Total encaissé")}
          </p>
          <p className="mt-1 text-3xl font-semibold tracking-tight tabular-nums text-slate-950">
            {formatEuros(locale, revenue.total_cents)}
          </p>
        </div>

        <ul className="min-h-0 divide-y divide-slate-100 border-y border-slate-100">
          <BreakdownRow
            label={t(locale, "Espèces")}
            value={formatEuros(locale, revenue.cash_cents)}
            dotClassName="bg-emerald-500"
          />
          <BreakdownRow
            label={t(locale, "Chèques")}
            value={formatEuros(locale, revenue.cheque_cents)}
            dotClassName="bg-indigo-500"
          />
          <BreakdownRow
            label={t(locale, "Cartes bancaires")}
            value={formatEuros(locale, revenue.card_cents)}
            dotClassName="bg-sky-500"
          />
        </ul>
      </div>

      {revenue.closed_session_count === 0 ? (
        <p className="mt-4 rounded-xl border border-dashed border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs text-slate-500">
          {t(locale, "Aucun suivi clôturé ne correspond à cette période.")}
        </p>
      ) : null}
    </section>
  );
}
