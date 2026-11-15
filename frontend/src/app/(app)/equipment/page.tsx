import { EquipmentGroups } from "@/components/equipment/equipment-groups";
import { apiFetch } from "@/lib/api";
import { getEnabledModules } from "@/lib/module-settings";
import { t } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import type { CashRegister, CurrentUser, Equipment, Vehicle } from "@/lib/types";

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
