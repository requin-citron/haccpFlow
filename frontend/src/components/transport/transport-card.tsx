import Link from "next/link";

import { PinIcon, TruckIcon } from "@/components/icons";
import { DeleteTransportButton } from "@/components/transport/delete-transport-button";
import { formatShortDay, formatTemperature } from "@/lib/format";
import { STATUS_ACCENTS, STATUS_BADGES, STATUS_DOTS, STATUS_LABELS } from "@/lib/status";
import { checkpointState } from "@/lib/transport";
import type { Transport } from "@/lib/types";

function CheckpointTile({
  label,
  time,
  temperature,
}: {
  label: string;
  time: string | null;
  temperature: number | null;
}) {
  const state = checkpointState(time, temperature);

  if (state === "empty") {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/70 px-4 py-3">
        <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">{label}</p>
        <p className="mt-1 text-sm text-slate-400">Non saisi</p>
      </div>
    );
  }

  return (
    <div className={`rounded-xl border px-4 py-3 ${STATUS_ACCENTS[state]}`}>
      <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-semibold tabular-nums text-slate-900">
        {temperature !== null ? formatTemperature(temperature) : "—"}
      </p>
      <p className="mt-0.5 text-xs text-slate-500">
        {time ? `à ${time.slice(0, 5)}` : "heure non saisie"}
      </p>
    </div>
  );
}

export function TransportCard({
  transport,
  isAdmin,
}: {
  transport: Transport;
  isAdmin: boolean;
}) {
  const state = transport.is_complete ? "complete" : "partial";

  return (
    <article className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300 hover:shadow-md">
      <header className="flex items-start gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-indigo-50 text-indigo-600 ring-1 ring-indigo-100">
          <TruckIcon className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="truncate font-semibold text-slate-900" title={transport.product_name}>
            {transport.product_name}
          </h3>
          <p className="mt-0.5 text-xs text-slate-500">
            {formatShortDay(transport.transport_date)}
            {transport.lot_number ? ` · Lot ${transport.lot_number}` : ""}
          </p>
        </div>
        <span
          className={`flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium ring-1 ring-inset ${STATUS_BADGES[state]}`}
        >
          <span className={`size-1.5 rounded-full ${STATUS_DOTS[state]}`} />
          {STATUS_LABELS[state]}
        </span>
      </header>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-slate-500">
        <span className="flex items-center gap-1.5">
          <PinIcon className="size-4 shrink-0" />
          {transport.place}
        </span>
        <span className="flex items-center gap-1.5">
          <TruckIcon className="size-4 shrink-0" />
          {transport.vehicle.name}
          {transport.vehicle.plate ? ` (${transport.vehicle.plate})` : ""}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <CheckpointTile
          label="Départ"
          time={transport.departure_time}
          temperature={transport.departure_temperature_celsius}
        />
        <CheckpointTile
          label="Arrivée"
          time={transport.arrival_time}
          temperature={transport.arrival_temperature_celsius}
        />
      </div>

      <footer className="mt-auto flex items-center justify-between gap-2 border-t border-slate-100 pt-4">
        <Link
          href={`/transport/${transport.id}`}
          className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-teal-700 transition hover:bg-teal-50"
        >
          Ouvrir
        </Link>
        {isAdmin ? (
          <DeleteTransportButton id={transport.id} label={transport.product_name} />
        ) : null}
      </footer>
    </article>
  );
}
