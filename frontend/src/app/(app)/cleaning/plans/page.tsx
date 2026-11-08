import Link from "next/link";

import { DeletePlanButton } from "@/components/cleaning/delete-plan-button";
import { CleaningPlanDialog } from "@/components/cleaning/plan-form-dialog";
import { DropletIcon } from "@/components/icons";
import { apiFetch } from "@/lib/api";
import {
  cleaningFrequencyLabel,
  daysBetween,
  formatShortDay,
  todayIso,
} from "@/lib/format";
import { plural, t } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import type { CleaningPlan, CleaningStatus, CurrentUser } from "@/lib/types";

const STATUS_BADGES: Record<CleaningStatus, string> = {
  overdue: "bg-rose-50 text-rose-700 ring-rose-200",
  due_today: "bg-amber-50 text-amber-700 ring-amber-200",
  upcoming: "bg-slate-100 text-slate-600 ring-slate-200",
};

function statusFor(nextDue: string, today: string): { status: CleaningStatus; days: number } {
  const days = daysBetween(today, nextDue);
  if (days < 0) {
    return { status: "overdue", days };
  }
  return { status: days === 0 ? "due_today" : "upcoming", days };
}

export default async function CleaningPlansPage() {
  const locale = await getLocale();
  const today = todayIso();
  const [user, plans] = await Promise.all([
    apiFetch<CurrentUser>("/api/v1/auth/me"),
    apiFetch<CleaningPlan[]>("/api/v1/cleaning-plans"),
  ]);
  const isAdmin = user.role === "admin";

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-teal-700">
            {t(locale, "Plan de maîtrise sanitaire")}
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 lg:text-3xl">
            {t(locale, "Plan de nettoyage")}
          </h1>
          <p className="mt-1 max-w-xl text-sm text-slate-500">
            {t(
              locale,
              "Déclare les zones et matériels à nettoyer, leur fréquence et les produits à utiliser. Les déclarations se font dans l'onglet Nettoyage.",
            )}
          </p>
        </div>
        <CleaningPlanDialog />
      </header>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <header className="border-b border-slate-100 px-5 py-4">
          <h2 className="text-base font-semibold text-slate-900">
            {plural(
              locale,
              { one: "{count} plan actif", other: "{count} plans actifs" },
              plans.length,
            )}
          </h2>
          <p className="text-xs text-slate-500">
            {t(
              locale,
              "Un plan désactivé disparaît de la liste mais son historique de nettoyages est conservé.",
            )}
          </p>
        </header>

        {plans.length === 0 ? (
          <div className="px-6 py-16 text-center">
            <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-slate-100 text-slate-500">
              <DropletIcon className="size-6" />
            </span>
            <h3 className="mt-4 text-base font-semibold text-slate-900">
              {t(locale, "Aucun plan défini")}
            </h3>
            <p className="mx-auto mt-1 max-w-sm text-sm text-slate-500">
              {t(
                locale,
                "Commence par déclarer une zone ou un matériel à nettoyer, avec sa fréquence.",
              )}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[52rem] text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-left text-[11px] uppercase tracking-wide text-slate-500">
                  <th className="px-5 py-3 font-medium">{t(locale, "Plan de nettoyage")}</th>
                  <th className="px-5 py-3 font-medium">{t(locale, "Fréquence")}</th>
                  <th className="px-5 py-3 font-medium">{t(locale, "Produits à utiliser")}</th>
                  <th className="px-5 py-3 font-medium">{t(locale, "Dernier nettoyage")}</th>
                  <th className="px-5 py-3 font-medium">{t(locale, "Prochaine échéance")}</th>
                  <th className="px-5 py-3 text-right font-medium">{t(locale, "Actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {plans.map((plan) => {
                  const due = plan.next_due_date ? statusFor(plan.next_due_date, today) : null;
                  return (
                    <tr key={plan.id} className="align-top">
                      <td className="px-5 py-3">
                        <Link
                          href={`/cleaning/${plan.id}`}
                          className="font-medium text-slate-900 transition hover:text-teal-700"
                        >
                          {plan.name}
                        </Link>
                      </td>
                      <td className="px-5 py-3 text-slate-600">
                        {cleaningFrequencyLabel(locale, plan.frequency)}
                      </td>
                      <td className="max-w-[18rem] px-5 py-3 text-slate-500">
                        {plan.products ?? "—"}
                      </td>
                      <td className="whitespace-nowrap px-5 py-3 text-slate-600">
                        {plan.last_cleaning_date
                          ? formatShortDay(locale, plan.last_cleaning_date)
                          : "—"}
                      </td>
                      <td className="whitespace-nowrap px-5 py-3">
                        {plan.next_due_date && due ? (
                          <span className="flex items-center gap-2">
                            <span className="text-slate-600">
                              {formatShortDay(locale, plan.next_due_date)}
                            </span>
                            <span
                              className={`rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset ${
                                STATUS_BADGES[due.status]
                              }`}
                            >
                              {due.status === "overdue"
                                ? t(locale, "{days} j de retard", { days: -due.days })
                                : due.status === "due_today"
                                  ? t(locale, "Aujourd'hui")
                                  : t(locale, "Dans {days} j", { days: due.days })}
                            </span>
                          </span>
                        ) : (
                          <span className="text-slate-400">{t(locale, "Après chaque usage")}</span>
                        )}
                      </td>
                      <td className="px-5 py-3">
                        <div className="flex items-center justify-end gap-1">
                          <CleaningPlanDialog plan={plan} />
                          {isAdmin ? <DeletePlanButton id={plan.id} name={plan.name} /> : null}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
