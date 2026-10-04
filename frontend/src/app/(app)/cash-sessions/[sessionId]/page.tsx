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
import { formatDateTimeUtc, formatDayLabel, formatEuros } from "@/lib/format";
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
  const isOpen = session.is_open;

  return (
    <div className="space-y-8">
      <div>
        <Link
          href="/cash-sessions"
          className="text-sm font-medium text-slate-500 transition hover:text-slate-800"
        >
          ← Retour aux suivis de caisse
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
              {formatDayLabel(session.session_date)}
            </p>
            <p className="mt-2 flex flex-wrap items-center gap-2">
              <span
                className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ring-1 ring-inset ${
                  isOpen
                    ? "bg-amber-50 text-amber-700 ring-amber-200"
                    : "bg-slate-100 text-slate-600 ring-slate-200"
                }`}
              >
                {isOpen ? "En cours" : "Clôturé"}
              </span>
              {session.opened_by_email ? (
                <span className="text-xs text-slate-500">
                  Ouvert par {session.opened_by_email}
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
            Télécharger le CSV
          </a>
          {isOpen ? <EditSessionDialog session={session} /> : null}
          {user.role === "admin" ? (
            <DeleteSessionButton id={session.id} label={session.cash_register_name} />
          ) : null}
        </div>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MoneyCard label="Fond de caisse" value={formatEuros(session.opening_total_cents)} />
        <MoneyCard
          label="Frais pro"
          value={formatEuros(session.expenses_professional_total_cents)}
        />
        <MoneyCard
          label="Frais perso"
          value={formatEuros(session.expenses_personal_total_cents)}
        />
        <MoneyCard
          label="Total des frais"
          value={formatEuros(session.expenses_total_cents)}
        />
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Fond d&apos;ouverture</h2>
          <p className="text-xs text-slate-500">
            Le comptage repris de la caisse à l&apos;ouverture du suivi.
          </p>
        </div>
        <CountsSummary
          counts={session.opening_counts}
          totalCents={session.opening_total_cents}
          label="Comptage d'ouverture"
        />
      </section>

      <section className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Frais{" "}
              <span className="text-sm font-normal text-slate-500">({session.expenses.length})</span>
            </h2>
            <p className="text-xs text-slate-500">
              {isOpen
                ? "Argent sorti de la caisse aujourd'hui : ajoute, corrige ou supprime une ligne à tout moment."
                : "Suivi clôturé : les frais sont figés et restent consultables."}
            </p>
          </div>
          {isOpen ? <ExpenseFormDialog sessionId={session.id} /> : null}
        </div>

        {session.expenses.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white/60 px-5 py-6 text-sm text-slate-500">
            Aucun frais enregistré sur ce suivi.
          </div>
        ) : (
          <ul className="space-y-2">
            {session.expenses.map((expense) => (
              <ExpenseRow
                key={expense.id}
                sessionId={session.id}
                expense={expense}
                isOpen={isOpen}
              />
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Clôture</h2>
          <p className="text-xs text-slate-500">
            {isOpen
              ? "Recompte la caisse en fin de journée : le comptage saisi devient l'état enregistré de la caisse."
              : "Le comptage de clôture a été enregistré comme nouvel état de la caisse."}
          </p>
        </div>

        {isOpen ? (
          <CloseSessionForm sessionId={session.id} />
        ) : (
          <div className="space-y-3">
            {session.closing_counts ? (
              <CountsSummary
                counts={session.closing_counts}
                totalCents={session.closing_total_cents ?? 0}
                label="Comptage de clôture"
              />
            ) : null}
            <p className="flex flex-wrap items-center gap-2 text-sm text-slate-600">
              <CheckIcon className="size-4 text-emerald-600" />
              {session.closed_by_email ? (
                <span>Clôturé par {session.closed_by_email}</span>
              ) : (
                <span>Clôturé</span>
              )}
              {session.closed_at ? (
                <span className="text-xs text-slate-500">
                  le {formatDateTimeUtc(session.closed_at)}
                </span>
              ) : null}
            </p>
            <Link
              href="/equipment"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
            >
              Voir la caisse dans le matériel
            </Link>
          </div>
        )}
      </section>
    </div>
  );
}
