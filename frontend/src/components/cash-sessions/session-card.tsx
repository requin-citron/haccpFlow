import Link from "next/link";

import { BanknoteIcon } from "@/components/icons";
import { formatDayLabel, formatEuros } from "@/lib/format";
import { SECONDARY_TRIGGER_CLASS } from "@/lib/ui";
import type { CashSession } from "@/lib/types";

export function SessionCard({ session }: { session: CashSession }) {
  return (
    <article className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300 hover:shadow-md">
      <header className="flex items-start gap-3">
        <span
          className={`grid size-10 shrink-0 place-items-center rounded-xl ring-1 ring-inset ${
            session.is_open
              ? "bg-amber-50 text-amber-600 ring-amber-100"
              : "bg-emerald-50 text-emerald-600 ring-emerald-100"
          }`}
        >
          <BanknoteIcon className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="truncate font-semibold text-slate-900" title={session.cash_register_name}>
            {session.cash_register_name}
          </h3>
          <p className="mt-0.5 text-xs capitalize text-slate-500">
            {formatDayLabel(session.session_date)}
          </p>
        </div>
        <span
          className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ring-1 ring-inset ${
            session.is_open
              ? "bg-amber-50 text-amber-700 ring-amber-200"
              : "bg-slate-100 text-slate-600 ring-slate-200"
          }`}
        >
          {session.is_open ? "En cours" : "Clôturé"}
        </span>
      </header>

      <dl className="grid grid-cols-2 gap-3">
        <div className="rounded-xl bg-slate-50 px-3.5 py-2.5">
          <dt className="text-[11px] font-medium uppercase tracking-wide text-slate-500">Fond</dt>
          <dd className="mt-0.5 font-semibold tabular-nums text-slate-900">
            {formatEuros(session.opening_total_cents)}
          </dd>
        </div>
        <div className="rounded-xl bg-slate-50 px-3.5 py-2.5">
          <dt className="text-[11px] font-medium uppercase tracking-wide text-slate-500">Frais</dt>
          <dd className="mt-0.5 font-semibold tabular-nums text-slate-900">
            {formatEuros(session.expenses_total_cents)}
          </dd>
        </div>
        {session.closing_total_cents !== null ? (
          <div className="col-span-2 rounded-xl bg-emerald-50 px-3.5 py-2.5">
            <dt className="text-[11px] font-medium uppercase tracking-wide text-emerald-700">
              Comptage de clôture
            </dt>
            <dd className="mt-0.5 font-semibold tabular-nums text-emerald-900">
              {formatEuros(session.closing_total_cents)}
            </dd>
          </div>
        ) : null}
      </dl>

      <p className="text-xs tabular-nums text-slate-500">
        Pro {formatEuros(session.expenses_professional_total_cents)} · perso{" "}
        {formatEuros(session.expenses_personal_total_cents)} · {session.expenses.length} frais
      </p>

      <footer className="mt-auto flex items-center justify-end border-t border-slate-100 pt-4">
        <Link href={`/cash-sessions/${session.id}`} className={SECONDARY_TRIGGER_CLASS}>
          {session.is_open ? "Continuer le suivi" : "Voir le détail"}
          <span aria-hidden="true">→</span>
        </Link>
      </footer>
    </article>
  );
}
