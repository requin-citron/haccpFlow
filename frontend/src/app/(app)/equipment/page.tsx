import { EquipmentGroups } from "@/components/equipment/equipment-groups";
import { FridgeIcon, GridIcon, SnowflakeIcon } from "@/components/icons";
import { apiFetch } from "@/lib/api";
import { getEnabledModules } from "@/lib/module-settings";
import { t } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import type { CashRegister, CurrentUser, Equipment, Vehicle } from "@/lib/types";

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
  const locale = await getLocale();
  const enabledModules = getEnabledModules();
  const [user, equipment, vehicles, cashRegisters] = await Promise.all([
    apiFetch<CurrentUser>("/api/v1/auth/me"),
    apiFetch<Equipment[]>("/api/v1/equipment"),
    enabledModules.transport
      ? apiFetch<Vehicle[]>("/api/v1/vehicles")
      : Promise.resolve([] as Vehicle[]),
    enabledModules.cashSessions
      ? apiFetch<CashRegister[]>("/api/v1/cash-registers")
      : Promise.resolve([] as CashRegister[]),
  ]);
  const isAdmin = user.role === "admin";
  const fridgeCount = equipment.filter((item) => item.type === "fridge").length;
  const freezerCount = equipment.length - fridgeCount;

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-teal-700">{t(locale, "Parc matériel")}</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 lg:text-3xl">
            {t(locale, "Matériel")}
          </h1>
          <p className="mt-1 max-w-xl text-sm text-slate-500">
            {t(locale, "Déclare les enceintes à surveiller et leurs seuils réglementaires.")}
            {enabledModules.readings
              ? t(locale, " Les relevés et l'enrôlement des capteurs arriveront ensuite.")
              : ""}
          </p>
        </div>
      </header>

      <section data-equipment-stats className="hidden gap-4 sm:grid sm:grid-cols-3">
        <StatCard
          label={t(locale, "Équipements actifs")}
          value={equipment.length}
          tone="slate"
          icon={<GridIcon className="size-5" />}
        />
        <StatCard
          label={t(locale, "Réfrigérateurs")}
          value={fridgeCount}
          tone="sky"
          icon={<FridgeIcon className="size-5" />}
        />
        <StatCard
          label={t(locale, "Congélateurs")}
          value={freezerCount}
          tone="indigo"
          icon={<SnowflakeIcon className="size-5" />}
        />
      </section>

      <EquipmentGroups
        equipment={equipment}
        vehicles={vehicles}
        cashRegisters={cashRegisters}
        isAdmin={isAdmin}
        includeVehicles={enabledModules.transport}
        includeCashRegisters={enabledModules.cashSessions}
      />
    </div>
  );
}
