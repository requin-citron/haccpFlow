import Link from "next/link";

import { SearchIcon, TruckIcon } from "@/components/icons";
import { TransportCard } from "@/components/transport/transport-card";
import { TransportFormDialog } from "@/components/transport/transport-form-dialog";
import { apiFetch } from "@/lib/api";
import { todayIso } from "@/lib/format";
import type { CurrentUser, Transport, Vehicle } from "@/lib/types";

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

export default async function TransportPage({
  searchParams,
}: {
  searchParams: Promise<{ lot?: string; from?: string; to?: string }>;
}) {
  const params = await searchParams;
  const lot = params.lot?.trim() ?? "";
  const from = params.from?.trim() ?? "";
  const to = params.to?.trim() ?? "";

  const query = new URLSearchParams();
  if (lot) {
    query.set("lot", lot);
  }
  if (from) {
    query.set("from", from);
  }
  if (to) {
    query.set("to", to);
  }
  const suffix = query.size > 0 ? `?${query.toString()}` : "";

  const [user, vehicles, transports] = await Promise.all([
    apiFetch<CurrentUser>("/api/v1/auth/me"),
    apiFetch<Vehicle[]>("/api/v1/vehicles"),
    apiFetch<Transport[]>(`/api/v1/transports${suffix}`),
  ]);
  const isAdmin = user.role === "admin";
  const ongoing = transports.filter((transport) => !transport.is_complete).length;
  const done = transports.length - ongoing;
  const filtered = Boolean(lot || from || to);

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-teal-700">Chaîne du froid</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 lg:text-3xl">
            Transport
          </h1>
          <p className="mt-1 max-w-xl text-sm text-slate-500">
            Chaque déplacement est enregistré au départ, puis complété à l&apos;arrivée avec les
            deux températures de la chaîne du froid.
          </p>
        </div>
        <TransportFormDialog vehicles={vehicles} defaultDate={todayIso()} />
      </header>

      <form action="/transport" method="get" className="flex flex-wrap items-end gap-3">
        <div className="relative min-w-[14rem] flex-1">
          <label htmlFor="lot" className="sr-only">
            Numéro de lot
          </label>
          <SearchIcon className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
          <input
            id="lot"
            name="lot"
            defaultValue={lot}
            placeholder="Rechercher un numéro de lot…"
            className="w-full rounded-xl border border-slate-300 bg-white py-2.5 pl-10 pr-3.5 text-sm text-slate-900 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-teal-500 focus:ring-4 focus:ring-teal-500/15"
          />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="from" className="block text-xs font-medium text-slate-600">
            Du
          </label>
          <input
            id="from"
            name="from"
            type="date"
            defaultValue={from}
            className="rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 shadow-sm outline-none transition focus:border-teal-500 focus:ring-4 focus:ring-teal-500/15"
          />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="to" className="block text-xs font-medium text-slate-600">
            Au
          </label>
          <input
            id="to"
            name="to"
            type="date"
            defaultValue={to}
            className="rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 shadow-sm outline-none transition focus:border-teal-500 focus:ring-4 focus:ring-teal-500/15"
          />
        </div>
        <button
          type="submit"
          className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50"
        >
          Filtrer
        </button>
        {filtered ? (
          <Link
            href="/transport"
            className="rounded-xl border border-teal-200 bg-teal-50 px-4 py-2.5 text-sm font-medium text-teal-700 transition hover:bg-teal-100"
          >
            Réinitialiser
          </Link>
        ) : null}
      </form>

      <section className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label={filtered ? "Transports trouvés" : "Transports enregistrés"}
          value={transports.length}
          tone="bg-slate-100 text-slate-600"
          icon={<TruckIcon className="size-5" />}
        />
        <StatCard
          label="En cours"
          value={ongoing}
          tone="bg-amber-50 text-amber-600"
          icon={<TruckIcon className="size-5" />}
        />
        <StatCard
          label="Terminés"
          value={done}
          tone="bg-emerald-50 text-emerald-600"
          icon={<TruckIcon className="size-5" />}
        />
      </section>

      {transports.length === 0 ? (
        <section className="rounded-2xl border border-dashed border-slate-300 bg-white/60 px-6 py-16 text-center">
          <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-slate-100 text-slate-500">
            <TruckIcon className="size-6" />
          </span>
          <h2 className="mt-4 text-base font-semibold text-slate-900">
            {filtered ? "Aucun transport ne correspond" : "Aucun transport enregistré"}
          </h2>
          <p className="mx-auto mt-1 max-w-sm text-sm text-slate-500">
            {filtered
              ? "Essaie un autre numéro de lot ou une autre plage de dates."
              : "Déclare un premier déplacement pour suivre la chaîne du froid."}
          </p>
        </section>
      ) : (
        <section className="grid gap-4 lg:grid-cols-2">
          {transports.map((transport) => (
            <TransportCard key={transport.id} transport={transport} isAdmin={isAdmin} />
          ))}
        </section>
      )}
    </div>
  );
}
