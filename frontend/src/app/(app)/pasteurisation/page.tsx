import Link from "next/link";

import { PasteurisationBatchDialog } from "@/components/pasteurisation/batch-form-dialog";
import { DeleteBatchButton } from "@/components/pasteurisation/delete-batch-button";
import { CheckIcon, FlameIcon, SearchIcon } from "@/components/icons";
import { apiFetch } from "@/lib/api";
import {
  PASTEURISATION_PHASE_LABELS,
  PASTEURISATION_PHASE_SHORT_LABELS,
  formatShortDay,
  todayIso,
} from "@/lib/format";
import {
  PHASE_STATE_DOTS,
  PHASE_STATE_LABELS,
  phaseState,
} from "@/lib/pasteurisation";
import type { CurrentUser, PasteurisationBatch } from "@/lib/types";

function StatCard({
  label,
  value,
  tone,
  icon,
}: {
  label: string;
  value: number;
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

export default async function PasteurisationPage({
  searchParams,
}: {
  searchParams: Promise<{ lot?: string }>;
}) {
  const params = await searchParams;
  const lot = params.lot?.trim() ?? "";
  const query = lot ? `?lot=${encodeURIComponent(lot)}` : "";

  const [user, batches] = await Promise.all([
    apiFetch<CurrentUser>("/api/v1/auth/me"),
    apiFetch<PasteurisationBatch[]>(`/api/v1/pasteurisations${query}`),
  ]);
  const isAdmin = user.role === "admin";
  const incomplete = batches.filter((batch) => !batch.is_complete).length;
  const remaining = batches.reduce(
    (total, batch) => total + (batch.phases.length - batch.filled_phases),
    0,
  );

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-teal-700">Point critique</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 lg:text-3xl">
            Pasteurisation
          </h1>
          <p className="mt-1 max-w-xl text-sm text-slate-500">
            Chaque lot est enregistré ici, puis ses trois phases se remplissent au fil de la
            production : préchauffage, palier, refroidissement.
          </p>
        </div>
        <PasteurisationBatchDialog defaultDate={todayIso()} />
      </header>

      <form action="/pasteurisation" method="get" className="flex flex-wrap gap-3">
        <div className="relative min-w-[16rem] flex-1">
          <SearchIcon className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
          <input
            name="lot"
            defaultValue={lot}
            placeholder="Rechercher un numéro de lot…"
            className="w-full rounded-xl border border-slate-300 bg-white py-2.5 pl-10 pr-3.5 text-sm text-slate-900 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-teal-500 focus:ring-4 focus:ring-teal-500/15"
          />
        </div>
        <button
          type="submit"
          className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50"
        >
          Rechercher
        </button>
        {lot ? (
          <Link
            href="/pasteurisation"
            className="rounded-xl border border-teal-200 bg-teal-50 px-4 py-2.5 text-sm font-medium text-teal-700 transition hover:bg-teal-100"
          >
            Tout afficher
          </Link>
        ) : null}
      </form>

      <section className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label={lot ? "Lots trouvés" : "Lots enregistrés"}
          value={batches.length}
          tone="bg-slate-100 text-slate-600"
          icon={<FlameIcon className="size-5" />}
        />
        <StatCard
          label="Lots incomplets"
          value={incomplete}
          tone="bg-amber-50 text-amber-600"
          icon={<FlameIcon className="size-5" />}
        />
        <StatCard
          label="Phases restantes"
          value={remaining}
          tone="bg-rose-50 text-rose-600"
          icon={<FlameIcon className="size-5" />}
        />
      </section>

      {batches.length === 0 ? (
        <section className="rounded-2xl border border-dashed border-slate-300 bg-white/60 px-6 py-16 text-center">
          <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-slate-100 text-slate-500">
            <FlameIcon className="size-6" />
          </span>
          <h2 className="mt-4 text-base font-semibold text-slate-900">
            {lot ? "Aucun lot ne correspond" : "Aucun lot enregistré"}
          </h2>
          <p className="mx-auto mt-1 max-w-sm text-sm text-slate-500">
            {lot
              ? "Essaie un autre numéro de lot, ou affiche tous les lots."
              : "Enregistre un premier lot de pasteurisation pour commencer le suivi."}
          </p>
        </section>
      ) : (
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[52rem] text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-left text-[11px] uppercase tracking-wide text-slate-500">
                  <th className="px-5 py-3 font-medium">Date</th>
                  <th className="px-5 py-3 font-medium">Produit</th>
                  <th className="px-5 py-3 font-medium">N° de lot</th>
                  <th className="px-5 py-3 font-medium">Entités</th>
                  <th className="px-5 py-3 font-medium">Phases</th>
                  <th className="px-5 py-3 font-medium">Statut</th>
                  <th className="px-5 py-3 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {batches.map((batch) => (
                  <tr key={batch.id} className="align-middle">
                    <td className="whitespace-nowrap px-5 py-3 text-slate-600">
                      {formatShortDay(batch.batch_date)}
                    </td>
                    <td className="px-5 py-3 font-medium text-slate-900">{batch.product_name}</td>
                    <td className="px-5 py-3 font-mono text-xs text-slate-600">
                      {batch.lot_number}
                    </td>
                    <td className="px-5 py-3 tabular-nums text-slate-600">{batch.quantity}</td>
                    <td className="px-5 py-3">
                      <span className="flex flex-wrap items-center gap-1.5">
                        {batch.phases.map((slot) => {
                          const state = phaseState(slot);
                          return (
                            <span
                              key={slot.phase}
                              title={`${PASTEURISATION_PHASE_LABELS[slot.phase]} — ${PHASE_STATE_LABELS[state]}`}
                              className="flex items-center gap-1 rounded-full bg-slate-50 px-2 py-0.5 ring-1 ring-inset ring-slate-200"
                            >
                              <span className={`size-1.5 rounded-full ${PHASE_STATE_DOTS[state]}`} />
                              <span className="text-[11px] text-slate-600">
                                {PASTEURISATION_PHASE_SHORT_LABELS[slot.phase]}
                              </span>
                            </span>
                          );
                        })}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <span
                        className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ring-1 ring-inset ${
                          batch.is_complete
                            ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
                            : "bg-amber-50 text-amber-700 ring-amber-200"
                        }`}
                      >
                        {batch.is_complete ? "Complet" : `${batch.filled_phases}/${batch.phases.length}`}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <Link
                          href={`/pasteurisation/${batch.id}`}
                          className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-teal-700 transition hover:bg-teal-50"
                        >
                          Ouvrir
                        </Link>
                        {isAdmin ? (
                          <DeleteBatchButton id={batch.id} lot={batch.lot_number} />
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {batches.length > 0 && incomplete === 0 ? (
        <p className="flex items-center gap-2 text-sm text-emerald-700">
          <CheckIcon className="size-4" />
          Tous les lots affichés ont leurs trois phases complètes.
        </p>
      ) : null}
    </div>
  );
}
