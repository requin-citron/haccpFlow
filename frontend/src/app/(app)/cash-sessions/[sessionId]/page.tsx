import Link from "next/link";
import { notFound } from "next/navigation";

import { CloseSessionForm } from "@/components/cash-sessions/close-session-form";
import { CountsSummary } from "@/components/cash-sessions/counts-summary";
import { DeleteSessionButton } from "@/components/cash-sessions/delete-session-button";
import { EditSessionDialog } from "@/components/cash-sessions/edit-session-dialog";
import { ExpenseFormDialog } from "@/components/cash-sessions/expense-form-dialog";
import { ExpenseRow } from "@/components/cash-sessions/expense-row";
import { BanknoteIcon, CheckIcon, DownloadIcon } from "@/components/icons";
import { ApiError, apiFetch } from "@/lib/api";
import { cashRegisterKindLabelKey, isPhysicalCash } from "@/lib/cash-register";
import { formatDateTimeUtc, formatDayLabel, formatEuros } from "@/lib/format";
import { t } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import { getEnabledModules } from "@/lib/module-settings";
import type { CashSession, CurrentUser } from "@/lib/types";

function MoneyCard({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-0.5 text-lg font-semibold tabular-nums ${tone ?? "text-slate-900"}`}>
        {value}
      </p>
    </div>
  );
}

export default async function CashSessionPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const locale = await getLocale();
  const { sessionId } = await params;

  let session: CashSession;
  try {
    session = await apiFetch<CashSession>(`/api/v1/cash-sessions/${sessionId}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const user = await apiFetch<CurrentUser>("/api/v1/auth/me");
  const enabledModules = getEnabledModules();
  const isOpen = session.is_open;
  const isCash = isPhysicalCash(session.cash_register_kind);

  return (
    <div className="space-y-8">
      <div>
        <Link
          href="/cash-sessions"
          className="text-sm font-medium text-slate-500 transition hover:text-slate-800"
        >
          ← {t(locale, "Retour aux suivis de caisse")}
        </Link>
      </div>

      <header className="flex flex-wrap items-start justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-start gap-4">
          <span
            className={`grid size-12 shrink-0 place-items-center rounded-2xl ${
              isOpen ? "bg-amber-50 text-amber-600" : "bg-emerald-50 text-emerald-600"
            }`}
          >
            <BanknoteIcon className="size-6" />
          </span>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
              {session.cash_register_name}
            </h1>
            <p className="mt-1 text-sm capitalize text-slate-500">
              {formatDayLabel(locale, session.session_date)}
            </p>
            <p className="mt-2 flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-teal-50 px-2.5 py-0.5 text-[11px] font-medium text-teal-700 ring-1 ring-inset ring-teal-200">
                {t(locale, cashRegisterKindLabelKey(session.cash_register_kind))}
              </span>
              <span
                className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ring-1 ring-inset ${
                  isOpen
                    ? "bg-amber-50 text-amber-700 ring-amber-200"
                    : "bg-slate-100 text-slate-600 ring-slate-200"
                }`}
              >
                {isOpen ? t(locale, "En cours") : t(locale, "Clôturé")}
              </span>
              {session.opened_by_email ? (
                <span className="text-xs text-slate-500">
                  {t(locale, "Ouvert par {email}", { email: session.opened_by_email })}
                </span>
              ) : null}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <a
            href={`/api/cash-sessions/${session.id}/export`}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
          >
            <DownloadIcon className="size-4" />
            {t(locale, "Télécharger le CSV")}
          </a>
          {isOpen ? <EditSessionDialog session={session} /> : null}
          {user.role === "admin" ? (
            <DeleteSessionButton id={session.id} label={session.cash_register_name} />
          ) : null}
        </div>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MoneyCard
          label={isCash ? t(locale, "Fond de caisse") : t(locale, "Encaissement du jour")}
          value={
            isCash
              ? formatEuros(locale, session.opening_total_cents)
              : session.collected_amount_cents === null
                ? "—"
                : formatEuros(locale, session.collected_amount_cents)
          }
        />
        <MoneyCard
          label={t(locale, "Frais pro")}
          value={formatEuros(locale, session.expenses_professional_total_cents)}
        />
        <MoneyCard
          label={t(locale, "Frais perso")}
          value={formatEuros(locale, session.expenses_personal_total_cents)}
        />
        <MoneyCard
          label={t(locale, "Total des frais")}
          value={formatEuros(locale, session.expenses_total_cents)}
        />
      </section>

      {isCash ? (
        <section className="space-y-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              {t(locale, "Fond d'ouverture")}
            </h2>
            <p className="text-xs text-slate-500">
              {t(locale, "Le comptage repris de la caisse à l'ouverture du suivi.")}
            </p>
          </div>
          <CountsSummary
            counts={session.opening_counts}
            totalCents={session.opening_total_cents}
            label={t(locale, "Comptage d'ouverture")}
            locale={locale}
          />
        </section>
      ) : null}

      <section className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              {t(locale, "Frais")}{" "}
              <span className="text-sm font-normal text-slate-500">({session.expenses.length})</span>
            </h2>
            <p className="text-xs text-slate-500">
              {isOpen
                ? t(locale, "Argent sorti de la caisse aujourd'hui : ajoute, corrige ou supprime une ligne à tout moment.")
                : t(locale, "Suivi clôturé : les frais sont figés et restent consultables.")}
            </p>
          </div>
          {isOpen ? <ExpenseFormDialog sessionId={session.id} /> : null}
        </div>

        {session.expenses.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white/60 px-5 py-6 text-sm text-slate-500">
            {t(locale, "Aucun frais enregistré sur ce suivi.")}
          </div>
        ) : (
          <ul className="space-y-2">
            {session.expenses.map((expense) => (
              <ExpenseRow
                key={expense.id}
                sessionId={session.id}
                expense={expense}
                isOpen={isOpen}
                locale={locale}
              />
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-base font-semibold text-slate-900">{t(locale, "Clôture")}</h2>
          <p className="text-xs text-slate-500">
            {isCash
              ? isOpen
                ? t(
                    locale,
                    "Recompte la caisse en fin de journée : le comptage saisi devient l'état enregistré de la caisse.",
                  )
                : t(
                    locale,
                    "Le comptage de clôture a été enregistré comme nouvel état de la caisse.",
                  )
              : isOpen
                ? t(locale, "Saisis le montant encaissé pour figer ce suivi.")
                : t(locale, "Le montant encaissé du suivi est enregistré.")}
          </p>
        </div>

        {isOpen ? (
          <CloseSessionForm session={session} />
        ) : (
          <div className="space-y-3">
            {isCash && session.closing_counts ? (
              <CountsSummary
                counts={session.closing_counts}
                totalCents={session.closing_total_cents ?? 0}
                label={t(locale, "Comptage de clôture")}
                locale={locale}
              />
            ) : null}
            {!isCash && session.collected_amount_cents !== null ? (
              <div className="rounded-xl bg-emerald-50 px-4 py-3">
                <p className="text-[11px] font-medium uppercase tracking-wide text-emerald-700">
                  {t(locale, "Encaissement du jour")}
                </p>
                <p className="mt-0.5 text-lg font-semibold tabular-nums text-emerald-900">
                  {formatEuros(locale, session.collected_amount_cents)}
                </p>
              </div>
            ) : null}
            <p className="flex flex-wrap items-center gap-2 text-sm text-slate-600">
              <CheckIcon className="size-4 text-emerald-600" />
              {session.closed_by_email ? (
                <span>{t(locale, "Clôturé par {email}", { email: session.closed_by_email })}</span>
              ) : (
                <span>{t(locale, "Clôturé")}</span>
              )}
              {session.closed_at ? (
                <span className="text-xs text-slate-500">
                  {t(locale, "le {date}", { date: formatDateTimeUtc(locale, session.closed_at) })}
                </span>
              ) : null}
            </p>
            {enabledModules.equipment ? (
              <Link
                href="/equipment"
                className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
              >
                {t(locale, "Voir la caisse dans le matériel")}
              </Link>
            ) : null}
          </div>
        )}
      </section>
    </div>
  );
}
