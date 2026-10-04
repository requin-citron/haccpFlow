import { EquipmentCard } from "@/components/equipment/equipment-card";
import { EquipmentFormDialog } from "@/components/equipment/equipment-form-dialog";
import { FridgeIcon, GridIcon, SnowflakeIcon } from "@/components/icons";
import { VehicleCard } from "@/components/vehicles/vehicle-card";
import { VehicleFormDialog } from "@/components/vehicles/vehicle-form-dialog";
import { apiFetch } from "@/lib/api";
import type { CurrentUser, Equipment, Vehicle } from "@/lib/types";

const STAT_TONES = {
  slate: "bg-slate-100 text-slate-600",
  sky: "bg-sky-50 text-sky-600",
  indigo: "bg-indigo-50 text-indigo-600",
} as const;

function StatCard({
  label,
  value,
  tone,
  icon,
}: {
  label: string;
  value: number;
  tone: keyof typeof STAT_TONES;
  icon: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
      <span className={`grid size-10 shrink-0 place-items-center rounded-xl ${STAT_TONES[tone]}`}>
        {icon}
      </span>
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
        <p className="text-2xl font-semibold tabular-nums text-slate-900">{value}</p>
      </div>
    </div>
  );
}

export default async function EquipmentPage() {
  const [user, equipment, vehicles] = await Promise.all([
    apiFetch<CurrentUser>("/api/v1/auth/me"),
    apiFetch<Equipment[]>("/api/v1/equipment"),
    apiFetch<Vehicle[]>("/api/v1/vehicles"),
  ]);
  const isAdmin = user.role === "admin";
  const fridgeCount = equipment.filter((item) => item.type === "fridge").length;
  const freezerCount = equipment.length - fridgeCount;

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-teal-700">Parc matériel</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 lg:text-3xl">
            Matériel
          </h1>
          <p className="mt-1 max-w-xl text-sm text-slate-500">
            Déclare les enceintes à surveiller et leurs seuils réglementaires. Les relevés et
            l&apos;enrôlement des capteurs arriveront ensuite.
          </p>
        </div>
        <EquipmentFormDialog />
      </header>

      <section className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Équipements actifs"
          value={equipment.length}
          tone="slate"
          icon={<GridIcon className="size-5" />}
        />
        <StatCard
          label="Réfrigérateurs"
          value={fridgeCount}
          tone="sky"
          icon={<FridgeIcon className="size-5" />}
        />
        <StatCard
          label="Congélateurs"
          value={freezerCount}
          tone="indigo"
          icon={<SnowflakeIcon className="size-5" />}
        />
      </section>

      {equipment.length === 0 ? (
        <section className="rounded-2xl border border-dashed border-slate-300 bg-white/60 px-6 py-16 text-center">
          <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-slate-100 text-slate-500">
            <FridgeIcon className="size-6" />
          </span>
          <h2 className="mt-4 text-base font-semibold text-slate-900">
            Aucun matériel pour l&apos;instant
          </h2>
          <p className="mx-auto mt-1 max-w-sm text-sm text-slate-500">
            Ajoute ton premier réfrigérateur ou congélateur pour commencer à suivre la chaîne du
            froid.
          </p>
        </section>
      ) : (
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {equipment.map((item) => (
            <EquipmentCard key={item.id} equipment={item} />
          ))}
        </section>
      )}

      <section className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Véhicules</h2>
            <p className="mt-0.5 text-xs text-slate-500">
              Les véhicules utilisés pour le suivi de transport. Ils se choisissent ensuite lors
              de la déclaration d&apos;un transport.
            </p>
          </div>
          <VehicleFormDialog />
        </div>

        {vehicles.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white/60 px-6 py-10 text-center">
            <p className="text-sm text-slate-500">
              Aucun véhicule enregistré. Ajoute un nom ou une plaque pour pouvoir déclarer des
              transports.
            </p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {vehicles.map((vehicle) => (
              <VehicleCard key={vehicle.id} vehicle={vehicle} isAdmin={isAdmin} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
