import Link from "next/link";

import { DeleteEquipmentButton } from "@/components/equipment/delete-equipment-button";
import { EquipmentFormDialog } from "@/components/equipment/equipment-form-dialog";
import { FridgeIcon, PinIcon, SnowflakeIcon } from "@/components/icons";
import { EQUIPMENT_TYPE_LABELS, formatDate, formatTemperatureRange } from "@/lib/format";
import type { Equipment } from "@/lib/types";

const TYPE_STYLES = {
  fridge: {
    icon: "bg-sky-50 text-sky-600 ring-sky-100",
    badge: "bg-sky-50 text-sky-700 ring-sky-200",
  },
  freezer: {
    icon: "bg-indigo-50 text-indigo-600 ring-indigo-100",
    badge: "bg-indigo-50 text-indigo-700 ring-indigo-200",
  },
} as const;

export function EquipmentCard({ equipment }: { equipment: Equipment }) {
  const styles = TYPE_STYLES[equipment.type];
  const Icon = equipment.type === "freezer" ? SnowflakeIcon : FridgeIcon;

  return (
    <article className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300 hover:shadow-md">
      <header className="flex items-start gap-3">
        <span className={`grid size-10 shrink-0 place-items-center rounded-xl ring-1 ${styles.icon}`}>
          <Icon className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="truncate font-semibold text-slate-900" title={equipment.name}>
            <Link
              href={`/equipment/${equipment.id}`}
              className="transition hover:text-teal-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
            >
              {equipment.name}
            </Link>
          </h3>
          <span
            className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${styles.badge}`}
          >
            {EQUIPMENT_TYPE_LABELS[equipment.type]}
          </span>
        </div>
      </header>

      <div className="rounded-xl bg-slate-50 px-4 py-3">
        <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
          Plage cible
        </p>
        <p className="mt-0.5 text-lg font-semibold tabular-nums text-slate-900">
          {formatTemperatureRange(
            equipment.min_temperature_celsius,
            equipment.max_temperature_celsius,
          )}
        </p>
      </div>

      {equipment.location ? (
        <p className="flex items-center gap-1.5 text-sm text-slate-500">
          <PinIcon className="size-4 shrink-0" />
          {equipment.location}
        </p>
      ) : null}

      {equipment.notes ? (
        <p className="line-clamp-2 text-sm text-slate-500" title={equipment.notes}>
          {equipment.notes}
        </p>
      ) : null}

      <p className="mt-auto text-xs text-slate-400">
        Ajouté le {formatDate(equipment.created_at)}
      </p>

      <footer className="flex items-center justify-between gap-2 border-t border-slate-100 pt-4">
        <EquipmentFormDialog equipment={equipment} />
        <DeleteEquipmentButton id={equipment.id} name={equipment.name} />
      </footer>
    </article>
  );
}
