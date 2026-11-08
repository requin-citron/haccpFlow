import Link from "next/link";

import { DayNavigation } from "@/components/readings/day-navigation";
import { ReadingDialog } from "@/components/readings/reading-dialog";
import { FridgeIcon, GridIcon, SnowflakeIcon } from "@/components/icons";
import { apiFetch } from "@/lib/api";
import {
  equipmentTypeLabel,
  formatTemperature,
  isIsoDate,
  readingSourceLabel,
  todayIso,
} from "@/lib/format";
import { t } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import { getEnabledModules } from "@/lib/module-settings";
import type { Equipment, TemperatureReadingDay, TemperatureReadingSlot } from "@/lib/types";

function SlotTile({
  label,
  slot,
  locale,
}: {
  label: string;
  slot: TemperatureReadingSlot | null;
  locale: Awaited<ReturnType<typeof getLocale>>;
}) {
  if (slot === null) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/70 px-4 py-3">
        <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">{label}</p>
        <p className="mt-1 text-sm text-slate-400">{t(locale, "Non saisi")}</p>
      </div>
    );
  }

  const tone = slot.is_compliant
    ? { box: "border-emerald-200 bg-emerald-50", value: "text-emerald-700" }
    : { box: "border-rose-200 bg-rose-50", value: "text-rose-700" };

  return (
    <div className={`rounded-xl border px-4 py-3 ${tone.box}`}>
      <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 text-lg font-semibold tabular-nums ${tone.value}`}>
        {formatTemperature(locale, slot.temperature_celsius)}
      </p>
      <p className="mt-0.5 text-xs text-slate-500">
        {readingSourceLabel(locale, slot.source)} ·{" "}
        {slot.is_compliant ? t(locale, "conforme") : t(locale, "hors seuils")}
      </p>
    </div>
  );
}

export default async function ReadingsPage({
  searchParams,
}: {
  searchParams: Promise<{ date?: string }>;
}) {
  const locale = await getLocale();
  const params = await searchParams;
  const date = isIsoDate(params.date) ? params.date : todayIso();
  const enabledModules = getEnabledModules();

  const equipmentList = await apiFetch<Equipment[]>("/api/v1/equipment");
  const rows = await Promise.all(
    equipmentList.map(async (equipment) => ({
      equipment,
      day: await apiFetch<TemperatureReadingDay>(
        `/api/v1/equipment/${equipment.id}/readings/${date}`,
      ),
    })),
  );

  const totalSlots = rows.length * 2;
  const filledSlots = rows.reduce(
    (total, row) => total + (row.day.morning ? 1 : 0) + (row.day.evening ? 1 : 0),
    0,
  );
  const missingSlots = totalSlots - filledSlots;

  return (
    <div className="space-y-8">
      <header className="space-y-5">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-teal-700">{t(locale, "Chaîne du froid")}</p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 lg:text-3xl">
              {t(locale, "Relevés de température")}
            </h1>
            <p className="mt-1 max-w-xl text-sm text-slate-500">
              {t(
                locale,
                "Deux relevés par jour et par équipement. Tu peux compléter le soir après avoir saisi le matin, ou rattraper une journée oubliée.",
              )}
            </p>
          </div>
          <DayNavigation date={date} />
        </div>

        {rows.length > 0 ? (
          <div className="flex flex-wrap items-center gap-4 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
            <div className="flex items-center gap-3">
              <span className="grid size-10 place-items-center rounded-xl bg-slate-100 text-slate-600">
                <GridIcon className="size-5" />
              </span>
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  {t(locale, "Créneaux saisis")}
                </p>
                <p className="text-xl font-semibold tabular-nums text-slate-900">
                  {filledSlots} / {totalSlots}
                </p>
              </div>
            </div>
            <p className="text-sm text-slate-500">
              {missingSlots === 0
                ? t(locale, "Journée complète, tout est saisi.")
                : missingSlots === 1
                  ? t(locale, "{count} créneau restant à saisir.", { count: missingSlots })
                  : t(locale, "{count} créneaux restants à saisir.", { count: missingSlots })}
            </p>
          </div>
        ) : null}
      </header>

      {rows.length === 0 ? (
        <section className="rounded-2xl border border-dashed border-slate-300 bg-white/60 px-6 py-16 text-center">
          <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-slate-100 text-slate-500">
            <FridgeIcon className="size-6" />
          </span>
          <h2 className="mt-4 text-base font-semibold text-slate-900">
            {t(locale, "Aucun matériel à relever")}
          </h2>
          <p className="mx-auto mt-1 max-w-sm text-sm text-slate-500">
            {enabledModules.equipment
              ? t(locale, "Déclare d'abord un réfrigérateur ou un congélateur dans la page Matériel.")
              : t(locale, "Aucun matériel disponible. Le module Matériel est désactivé.")}
          </p>
          {enabledModules.equipment ? (
            <Link
              href="/equipment"
              className="mt-6 inline-flex items-center gap-2 rounded-xl bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700"
            >
              {t(locale, "Gérer le matériel")}
            </Link>
          ) : null}
        </section>
      ) : (
        <section className="grid gap-4 lg:grid-cols-2">
          {rows.map(({ equipment, day }) => {
            const Icon = equipment.type === "freezer" ? SnowflakeIcon : FridgeIcon;
            return (
              <article
                key={equipment.id}
                className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
              >
                <header className="flex items-start gap-3">
                  <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-slate-100 text-slate-600">
                    <Icon className="size-5" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <h3 className="truncate font-semibold text-slate-900">{equipment.name}</h3>
                    <p className="text-xs text-slate-500">
                      {equipmentTypeLabel(locale, equipment.type)} ·{" "}
                      {formatTemperature(locale, equipment.min_temperature_celsius)} –{" "}
                      {formatTemperature(locale, equipment.max_temperature_celsius)}
                    </p>
                  </div>
                  <ReadingDialog equipment={equipment} readingDate={date} day={day} />
                </header>

                <div className="grid grid-cols-2 gap-3">
                  <SlotTile label={t(locale, "Matin")} slot={day.morning} locale={locale} />
                  <SlotTile label={t(locale, "Soir")} slot={day.evening} locale={locale} />
                </div>
              </article>
            );
          })}
        </section>
      )}
    </div>
  );
}
