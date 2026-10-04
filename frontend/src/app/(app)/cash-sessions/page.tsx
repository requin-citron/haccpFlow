import Link from "next/link";

import { OpenSessionDialog } from "@/components/cash-sessions/open-session-dialog";
import { SessionCard } from "@/components/cash-sessions/session-card";
import { BanknoteIcon, CheckIcon, GridIcon } from "@/components/icons";
import { apiFetch } from "@/lib/api";
import { formatEuros } from "@/lib/format";
import type { CashRegister, CashSession } from "@/lib/types";

function StatCard({
  label,
  value,
  tone,
  icon,
}: {
  label: string;
  value: string | number;
  tone: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
      <span className={`grid size-10 shrink-0 place-items-center rounded-xl ${tone}`}>{icon}</span>
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
        <p className="text-2xl font-semibold tabular-nums text-slate-900">{value}</p>
      </div>
    </div>
  );
}

export default async function CashSessionsPage() {
  const [cashRegisters, sessions] = await Promise.all([
    apiFetch<CashRegister[]>("/api/v1/cash-registers"),
    apiFetch<CashSession[]>("/api/v1/cash-sessions"),
  ]);

  const openSessions = sessions.filter((session) => session.is_open);
  const closedSessions = sessions.filter((session) => !session.is_open);
  const openExpensesCents = openSessions.reduce(
    (total, session) => total + session.expenses_total_cents,
    0,
  );

  // Only a register without an open session can be tracked: the API refuses
  // a second one, so the choice is filtered here to avoid a dead end.
  const trackedRegisterIds = new Set(openSessions.map((session) => session.cash_register_id));
  const freeRegisters = cashRegisters.filter(
    (cashRegister) => !trackedRegisterIds.has(cashRegister.id),
  );

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-teal-700">Caisse</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 lg:text-3xl">
            Suivi de caisse
          </h1>
          <p className="mt-1 max-w-xl text-sm text-slate-500">
            Ouvre un suivi, enregistre les frais pro et perso de la journée, puis clôture en
            recomptant la caisse : ce comptage devient l&apos;état enregistré.
          </p>
        </div>
        {cashRegisters.length > 0 ? (
          <div className="flex flex-col items-end gap-1">
            <OpenSessionDialog cashRegisters={freeRegisters} />
            {freeRegisters.length === 0 ? (
              <p className="max-w-xs text-right text-xs text-slate-500">
                Chaque caisse a déjà un suivi ouvert : clôture-en un pour en ouvrir un autre.
              </p>
            ) : null}
          </div>
        ) : null}
      </header>

      {cashRegisters.length === 0 ? (
        <section className="rounded-2xl border border-dashed border-slate-300 bg-white/60 px-6 py-16 text-center">
          <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-slate-100 text-slate-500">
            <BanknoteIcon className="size-6" />
          </span>
          <h2 className="mt-4 text-base font-semibold text-slate-900">Aucune caisse enrôlée</h2>
          <p className="mx-auto mt-1 max-w-sm text-sm text-slate-500">
            Enrôle d&apos;abord une caisse et son comptage initial dans l&apos;onglet Matériel.
          </p>
          <Link
            href="/equipment"
            className="mt-6 inline-flex items-center gap-2 rounded-xl bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700"
          >
            Aller au matériel
          </Link>
        </section>
      ) : (
        <>
          <section className="grid gap-4 sm:grid-cols-3">
            <StatCard
              label="Suivis en cours"
              value={openSessions.length}
              tone="bg-amber-50 text-amber-600"
              icon={<BanknoteIcon className="size-5" />}
            />
            <StatCard
              label="Caisses enrôlées"
              value={cashRegisters.length}
              tone="bg-slate-100 text-slate-600"
              icon={<GridIcon className="size-5" />}
            />
            <StatCard
              label="Frais des suivis en cours"
              value={formatEuros(openExpensesCents)}
              tone="bg-emerald-50 text-emerald-600"
              icon={<CheckIcon className="size-5" />}
            />
          </section>

          <section className="space-y-4">
            <div>
              <h2 className="text-base font-semibold text-slate-900">Suivis en cours</h2>
              <p className="text-xs text-slate-500">
                Une seule ouverture à la fois par caisse : clôture le suivi avant d&apos;en ouvrir
                un autre sur la même caisse.
              </p>
            </div>

            {openSessions.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-white/60 px-5 py-6 text-sm text-slate-500">
                Aucun suivi ouvert : commence la journée en ouvrant un suivi sur une caisse.
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {openSessions.map((session) => (
                  <SessionCard key={session.id} session={session} />
                ))}
              </div>
            )}
          </section>

          <section className="space-y-4">
            <div>
              <h2 className="text-base font-semibold text-slate-900">Suivis clôturés</h2>
              <p className="text-xs text-slate-500">
                Chaque clôture a enregistré le comptage de fin de journée dans la caisse.
              </p>
            </div>

            {closedSessions.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-white/60 px-5 py-6 text-sm text-slate-500">
                Aucun suivi clôturé pour l&apos;instant.
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {closedSessions.map((session) => (
                  <SessionCard key={session.id} session={session} />
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
