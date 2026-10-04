import Link from "next/link";
import { notFound } from "next/navigation";

import { PinIcon, TruckIcon } from "@/components/icons";
import { DeleteTransportButton } from "@/components/transport/delete-transport-button";
import { TransportCheckpointForm } from "@/components/transport/checkpoint-form";
import { TransportFormDialog } from "@/components/transport/transport-form-dialog";
import { TransportNoteForm } from "@/components/transport/transport-note-form";
import { ApiError, apiFetch } from "@/lib/api";
import { formatDayLabel, todayIso } from "@/lib/format";
import { STATUS_BADGES } from "@/lib/status";
import type { CurrentUser, Transport, Vehicle } from "@/lib/types";

export default async function TransportDetailPage({
  params,
}: {
  params: Promise<{ transportId: string }>;
}) {
  const { transportId } = await params;

  let transport: Transport;
  try {
    transport = await apiFetch<Transport>(`/api/v1/transports/${transportId}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const [user, vehicles] = await Promise.all([
    apiFetch<CurrentUser>("/api/v1/auth/me"),
    apiFetch<Vehicle[]>("/api/v1/vehicles"),
  ]);

  return (
    <div className="space-y-8">
      <div>
        <Link
          href="/transport"
          className="text-sm font-medium text-slate-500 transition hover:text-slate-800"
        >
          ← Retour aux transports
        </Link>
      </div>

      <header className="flex flex-wrap items-start justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-start gap-4">
          <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-indigo-50 text-indigo-600">
            <TruckIcon className="size-6" />
          </span>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
              {transport.product_name}
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              {transport.lot_number ? (
                <>
                  Lot <span className="font-mono text-slate-700">{transport.lot_number}</span> ·{" "}
                </>
              ) : null}
              <span className="capitalize">{formatDayLabel(transport.transport_date)}</span>
            </p>
            <p className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-slate-500">
              <span className="flex items-center gap-1.5">
                <PinIcon className="size-4 shrink-0" />
                {transport.place}
              </span>
              <span className="flex items-center gap-1.5">
                <TruckIcon className="size-4 shrink-0" />
                {transport.vehicle.name}
                {transport.vehicle.plate ? ` (${transport.vehicle.plate})` : ""}
                {transport.vehicle.id === null ? " · non référencé" : ""}
              </span>
            </p>
            <p className="mt-3">
              <span
                className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ring-1 ring-inset ${
                  STATUS_BADGES[transport.is_complete ? "complete" : "partial"]
                }`}
              >
                {transport.is_complete ? "Chaîne du froid complète" : "Transport en cours"}
              </span>
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <TransportFormDialog
            vehicles={vehicles}
            transport={transport}
            defaultDate={todayIso()}
          />
          {user.role === "admin" ? (
            <DeleteTransportButton id={transport.id} label={transport.product_name} />
          ) : null}
        </div>
      </header>

      <section className="space-y-4">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Relevés de température</h2>
          <p className="text-xs text-slate-500">
            Saisis le départ avant de partir, puis l&apos;arrivée à la livraison. Chaque
            enregistrement est indépendant, et les corrections sont journalisées.
          </p>
        </div>

        <div className="space-y-4">
          <TransportCheckpointForm
            transportId={transport.id}
            kind="departure"
            title="Départ"
            rank={1}
            time={transport.departure_time}
            temperature={transport.departure_temperature_celsius}
          />
          <TransportCheckpointForm
            transportId={transport.id}
            kind="arrival"
            title="Arrivée"
            rank={2}
            time={transport.arrival_time}
            temperature={transport.arrival_temperature_celsius}
          />
          <TransportNoteForm transportId={transport.id} observation={transport.observation} />
        </div>
      </section>
    </div>
  );
}
