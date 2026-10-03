import Link from "next/link";
import { notFound } from "next/navigation";

import { FridgeIcon, PinIcon, SnowflakeIcon } from "@/components/icons";
import { ReadingDialog } from "@/components/readings/reading-dialog";
import { apiFetch } from "@/lib/api";
import {
  EQUIPMENT_TYPE_LABELS,
  SLOT_LABELS,
  addDays,
  formatDateTimeUtc,
  formatShortDay,
  formatTemperature,
  todayIso,
} from "@/lib/format";
import type {
  Equipment,
  TemperatureReadingDay,
  TemperatureReadingEdit,
  TemperatureReadingSlot,
} from "@/lib/types";

const HISTORY_DAYS = 14;

function SlotValue({ slot }: { slot: TemperatureReadingSlot | null }) {
  if (slot === null) {
    return <span className="text-slate-400">—</span>;
  }
  return (
    <span
      className={`font-medium tabular-nums ${
        slot.is_compliant ? "text-emerald-700" : "text-rose-700"
      }`}
    >
      {formatTemperature(slot.temperature_celsius)}
    </span>
  );
}

function HistoryCell({ entries }: { entries: TemperatureReadingEdit[] }) {
  if (entries.length === 0) {
    return <span className="text-xs text-slate-400">—</span>;
  }
  return (
    <details className="group">
      <summary className="cursor-pointer list-none text-xs font-semibold text-teal-700 hover:text-teal-800">
        Voir ({entries.length})
      </summary>
      <ul className="mt-2 space-y-1.5">
        {entries.map((entry, index) => (
          <li
            key={`${entry.slot}-${entry.changed_at}-${index}`}
            className="rounded-lg bg-slate-50 px-2.5 py-2 text-[11px] leading-relaxed text-slate-600"
          >
            <span className="font-medium text-slate-800">{SLOT_LABELS[entry.slot]}</span>{" "}
            {entry.action === "created" ? "créé" : "modifié"}
            {entry.previous_celsius !== null
              ? ` · ${formatTemperature(entry.previous_celsius)} → ${formatTemperature(entry.new_celsius)}`
              : ` · ${formatTemperature(entry.new_celsius)}`}
            <br />
            {formatDateTimeUtc(entry.changed_at)}
            {entry.changed_by_email ? ` · ${entry.changed_by_email}` : ""}
          </li>
        ))}
      </ul>
    </details>
  );
}

export default async function EquipmentDetailPage({
  params,
}: {
  params: Promise<{ equipmentId: string }>;
}) {
  const { equipmentId } = await params;

  const equipmentList = await apiFetch<Equipment[]>("/api/v1/equipment");
  const equipment = equipmentList.find((item) => item.id === equipmentId);
  if (!equipment) {
    notFound();
  }

  const to = todayIso();
  const from = addDays(to, -(HISTORY_DAYS - 1));
  const days = await apiFetch<TemperatureReadingDay[]>(
    `/api/v1/equipment/${equipment.id}/readings?from=${from}&to=${to}`,
  );

  const rows = await Promise.all(
    [...days].reverse().map(async (day) => ({
      day,
      history:
        day.morning || day.evening
          ? await apiFetch<TemperatureReadingEdit[]>(
              `/api/v1/equipment/${equipment.id}/readings/${day.reading_date}/history`,
            )
          : [],
    })),
  );

  const Icon = equipment.type === "freezer" ? SnowflakeIcon : FridgeIcon;

  return (
    <div className="space-y-8">
      <div>
        <Link
          href="/equipment"
          className="text-sm font-medium text-slate-500 transition hover:text-slate-800"
        >
          ← Retour au matériel
        </Link>
      </div>

      <header className="flex flex-wrap items-start justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-start gap-4">
          <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-slate-100 text-slate-600">
            <Icon className="size-6" />
          </span>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
              {equipment.name}
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              {EQUIPMENT_TYPE_LABELS[equipment.type]} · plage cible{" "}
              {formatTemperature(equipment.min_temperature_celsius)} à{" "}
              {formatTemperature(equipment.max_temperature_celsius)}
            </p>
            {equipment.location ? (
              <p className="mt-1 flex items-center gap-1.5 text-sm text-slate-500">
                <PinIcon className="size-4" />
                {equipment.location}
              </p>
            ) : null}
            {equipment.notes ? (
              <p className="mt-2 max-w-xl text-sm text-slate-500">{equipment.notes}</p>
            ) : null}
          </div>
        </div>
        <Link
          href="/readings"
          className="rounded-xl bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700"
        >
          Saisir un relevé
        </Link>
      </header>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              {HISTORY_DAYS} derniers jours
            </h2>
            <p className="text-xs text-slate-500">
              Chaque modification est tracée : auteur et valeur précédente.
            </p>
          </div>
        </header>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[36rem] text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-[11px] uppercase tracking-wide text-slate-500">
                <th className="px-5 py-3 font-medium">Jour</th>
                <th className="px-5 py-3 font-medium">Matin</th>
                <th className="px-5 py-3 font-medium">Soir</th>
                <th className="px-5 py-3 font-medium">Saisie</th>
                <th className="px-5 py-3 font-medium">Journal</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map(({ day, history }) => (
                <tr key={day.reading_date} className="align-top">
                  <td className="whitespace-nowrap px-5 py-3 capitalize text-slate-700">
                    {formatShortDay(day.reading_date)}
                  </td>
                  <td className="px-5 py-3">
                    <SlotValue slot={day.morning} />
                  </td>
                  <td className="px-5 py-3">
                    <SlotValue slot={day.evening} />
                  </td>
                  <td className="px-5 py-3">
                    <ReadingDialog equipment={equipment} readingDate={day.reading_date} day={day} />
                  </td>
                  <td className="px-5 py-3">
                    <HistoryCell entries={history} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
