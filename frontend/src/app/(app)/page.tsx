import { redirect } from "next/navigation";

import { ConfigurableDashboard } from "@/components/dashboard/configurable-dashboard";
import { DashboardTimeRangePicker } from "@/components/dashboard/time-range-picker";
import { AlertIcon, DashboardIcon } from "@/components/icons";
import { apiFetch } from "@/lib/api";
import { requireCurrentUser } from "@/lib/current-user";
import { resolveDashboardRange } from "@/lib/dashboard";
import { todayIso } from "@/lib/format";
import { getEnabledModules } from "@/lib/module-settings";
import { t } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import { firstEnabledModuleHref } from "@/lib/modules";
import type {
  DashboardLayout,
  DashboardMissingReadings,
  DashboardRevenue,
} from "@/lib/types";

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<{ from?: string; to?: string }>;
}) {
  const locale = await getLocale();
  const user = await requireCurrentUser();
  const enabledModules = getEnabledModules();

  if (!enabledModules.dashboard) {
    const destination = firstEnabledModuleHref(enabledModules, user.role === "admin");
    if (destination) {
      redirect(destination);
    }

    return (
      <div className="mx-auto max-w-lg rounded-2xl border border-amber-200 bg-amber-50 px-6 py-12 text-center">
        <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-amber-100 text-amber-700">
          <AlertIcon className="size-6" />
        </span>
        <h1 className="mt-4 text-lg font-semibold text-slate-900">
          {t(locale, "Aucun module actif")}
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          {t(
            locale,
            "Active au moins un module dans le fichier .env, puis recrée le service frontend avec docker compose up -d.",
          )}
        </p>
      </div>
    );
  }

  const params = await searchParams;
  const today = todayIso();
  const range = resolveDashboardRange(params, today);
  const layout = await apiFetch<DashboardLayout>("/api/v1/dashboard/layout");
  const revenueQuery = new URLSearchParams({
    from: range.from,
    to: range.to,
  });
  const includesRevenue = layout.widgets.some((widget) => widget.key === "revenue");
  const includesMissingReadings = layout.widgets.some(
    (widget) => widget.key === "missing_readings",
  );
  const [revenue, missingReadings] = await Promise.all([
    includesRevenue
      ? apiFetch<DashboardRevenue>(
          `/api/v1/dashboard/revenue?${revenueQuery.toString()}`,
        )
      : Promise.resolve(null),
    includesMissingReadings
      ? apiFetch<DashboardMissingReadings>(
          `/api/v1/dashboard/missing-readings?${revenueQuery.toString()}`,
        )
      : Promise.resolve(null),
  ]);

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-start justify-end gap-5 sm:justify-between">
        <div className="hidden items-start gap-4 sm:flex">
          <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-teal-50 text-teal-700 ring-1 ring-teal-100">
            <DashboardIcon className="size-6" />
          </span>
          <div>
            <p className="text-sm font-medium text-teal-700">{t(locale, "Vue d'ensemble")}</p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 lg:text-3xl">
              {t(locale, "Tableau de bord")}
            </h1>
            <p className="mt-1 max-w-2xl text-sm text-slate-500">
              {t(
                locale,
                "Explore une période pour préparer une vue consolidée de l'activité. Les widgets seront ajoutés progressivement.",
              )}
            </p>
          </div>
        </div>
        <DashboardTimeRangePicker range={range} today={today} />
      </header>

      <ConfigurableDashboard
        initialLayout={layout}
        initialRevenue={revenue}
        initialMissingReadings={missingReadings}
        periodFrom={range.from}
        periodTo={range.to}
        locale={locale}
      />
    </div>
  );
}
