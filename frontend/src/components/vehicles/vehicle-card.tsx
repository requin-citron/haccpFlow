import { TruckIcon } from "@/components/icons";
import { DeleteVehicleButton } from "@/components/vehicles/delete-vehicle-button";
import { VehicleFormDialog } from "@/components/vehicles/vehicle-form-dialog";
import { formatDate } from "@/lib/format";
import type { Vehicle } from "@/lib/types";

export function VehicleCard({ vehicle, isAdmin }: { vehicle: Vehicle; isAdmin: boolean }) {
  const label = vehicle.name ?? vehicle.plate ?? "Véhicule";

  return (
    <article className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300 hover:shadow-md">
      <header className="flex items-start gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-indigo-50 text-indigo-600 ring-1 ring-indigo-100">
          <TruckIcon className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="truncate font-semibold text-slate-900" title={label}>
            {label}
          </h3>
          <span className="mt-1 inline-flex rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700 ring-1 ring-inset ring-indigo-200">
            Véhicule
          </span>
        </div>
      </header>

      <div className="rounded-xl bg-slate-50 px-4 py-3">
        <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">Plaque</p>
        <p className="mt-0.5 text-lg font-semibold tabular-nums text-slate-900">
          {vehicle.plate ?? "Non renseignée"}
        </p>
      </div>

      <p className="mt-auto text-xs text-slate-400">Ajouté le {formatDate(vehicle.created_at)}</p>

      <footer className="flex items-center justify-between gap-2 border-t border-slate-100 pt-4">
        <VehicleFormDialog vehicle={vehicle} />
        {isAdmin ? <DeleteVehicleButton id={vehicle.id} label={label} /> : null}
      </footer>
    </article>
  );
}
