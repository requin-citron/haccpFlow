import Link from "next/link";

import { DeclareCleaningDialog } from "@/components/cleaning/declare-cleaning-dialog";
import { AlertIcon, CheckIcon, DropletIcon, GridIcon } from "@/components/icons";
import { apiFetch } from "@/lib/api";
import {
  CLEANING_FREQUENCY_LABELS,
  daysBetween,
  formatShortDay,
  todayIso,
} from "@/lib/format";
import type { CleaningPlan, CleaningScheduleEntry, CleaningStatus } from "@/lib/types";

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

function StatCard({
  label,
  value,
  tone,
  icon,
}: {
  label: string;
  value: number;
  tone: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
      <span className={`grid size-10 shrink-0 place-items-center rounded-xl ${tone}`}>{icon}</span>
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
        <p className="text-2xl font-semibold tabular-nums text-slate-900">{value}</p>
      </div>
    </div>
  );
}

export default async function CleaningPage() {
  const today = todayIso();
  const [plans, schedule] = await Promise.all([
    apiFetch<CleaningPlan[]>("/api/v1/cleaning-plans"),
    apiFetch<CleaningScheduleEntry[]>("/api/v1/cleaning-schedule"),
  ]);

  const overdue = schedule.filter((entry) => entry.status === "overdue");
  const dueToday = schedule.filter((entry) => entry.status === "due_today");
  const toHandle = [...overdue, ...dueToday];

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-teal-700">Plan de maîtrise sanitaire</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 lg:text-3xl">
            Nettoyage
          </h1>
          <p className="mt-1 max-w-xl text-sm text-slate-500">
            Ce qu&apos;il reste à nettoyer, et la déclaration des nettoyages réalisés. Le
            prévisionnel se recalcule à partir du dernier nettoyage déclaré.
          </p>
        </div>
        <Link
          href="/cleaning/plans"
          className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
        >
          Gérer les plans
        </Link>
      </header>

      <section className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="En retard"
          value={overdue.length}
          tone="bg-rose-50 text-rose-600"
          icon={<AlertIcon className="size-5" />}
        />
        <StatCard
          label="À faire aujourd'hui"
          value={dueToday.length}
          tone="bg-amber-50 text-amber-600"
          icon={<CheckIcon className="size-5" />}
        />
        <StatCard
          label="Plans actifs"
          value={plans.length}
          tone="bg-slate-100 text-slate-600"
          icon={<GridIcon className="size-5" />}
        />
      </section>

      <section className="space-y-4">
        <h2 className="text-base font-semibold text-slate-900">À traiter</h2>
        {toHandle.length === 0 ? (
          <div className="flex items-center gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-800">
            <CheckIcon className="size-5 shrink-0" />
            Rien à nettoyer pour l&apos;instant : tout est à jour.
          </div>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">
            {toHandle.map((entry) => {
              const late = entry.status === "overdue";
              return (
                <article
                  key={entry.plan_id}
                  className={`flex flex-col gap-3 rounded-2xl border bg-white p-5 shadow-sm ${
                    late ? "border-rose-200" : "border-amber-200"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="truncate font-semibold text-slate-900">{entry.name}</h3>
                      <p className="text-xs text-slate-500">
                        {CLEANING_FREQUENCY_LABELS[entry.frequency]}
                        {entry.last_cleaning_date
                          ? ` · dernier le ${formatShortDay(entry.last_cleaning_date)}`
                          : " · jamais nettoyé"}
                      </p>
                    </div>
                    <span
                      className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${
                        STATUS_BADGES[entry.status]
                      }`}
                    >
                      {late ? `En retard de ${entry.days_late} j` : "Aujourd'hui"}
                    </span>
                  </div>

                  {entry.products ? (
                    <p className="text-sm text-slate-500">{entry.products}</p>
                  ) : null}

                  <div className="mt-auto flex items-center justify-between gap-2 pt-1">
                    <Link
                      href={`/cleaning/${entry.plan_id}`}
                      className="text-xs font-medium text-slate-500 transition hover:text-slate-800"
                    >
                      Voir l&apos;historique
                    </Link>
                    <DeclareCleaningDialog
                      plan={{ id: entry.plan_id, name: entry.name }}
                      defaultDate={today}
                      compact
                    />
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <header className="border-b border-slate-100 px-5 py-4">
          <h2 className="text-base font-semibold text-slate-900">Tous les plans</h2>
          <p className="text-xs text-slate-500">
            Déclare un nettoyage directement depuis la ligne. Les nettoyages après chaque usage
            n&apos;ont pas d&apos;échéance.
          </p>
        </header>

        {plans.length === 0 ? (
          <div className="px-6 py-16 text-center">
            <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-slate-100 text-slate-500">
              <DropletIcon className="size-6" />
            </span>
            <h3 className="mt-4 text-base font-semibold text-slate-900">Aucun plan défini</h3>
            <p className="mx-auto mt-1 max-w-sm text-sm text-slate-500">
              Commence par créer un plan dans l&apos;onglet « Plan de nettoyage ».
            </p>
            <Link
              href="/cleaning/plans"
              className="mt-6 inline-flex items-center gap-2 rounded-xl bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700"
            >
              Créer un plan
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[52rem] text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-left text-[11px] uppercase tracking-wide text-slate-500">
                  <th className="px-5 py-3 font-medium">Plan</th>
                  <th className="px-5 py-3 font-medium">Fréquence</th>
                  <th className="px-5 py-3 font-medium">Produits</th>
                  <th className="px-5 py-3 font-medium">Dernier</th>
                  <th className="px-5 py-3 font-medium">Prochaine échéance</th>
                  <th className="px-5 py-3 text-right font-medium">Actions</th>
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
                        {CLEANING_FREQUENCY_LABELS[plan.frequency]}
                      </td>
                      <td className="max-w-[16rem] px-5 py-3 text-slate-500">
                        {plan.products ?? "—"}
                      </td>
                      <td className="whitespace-nowrap px-5 py-3 text-slate-600">
                        {plan.last_cleaning_date ? formatShortDay(plan.last_cleaning_date) : "—"}
                      </td>
                      <td className="whitespace-nowrap px-5 py-3">
                        {plan.next_due_date && due ? (
                          <span className="flex items-center gap-2">
                            <span className="text-slate-600">
                              {formatShortDay(plan.next_due_date)}
                            </span>
                            <span
                              className={`rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset ${
                                STATUS_BADGES[due.status]
                              }`}
                            >
                              {due.status === "overdue"
                                ? `${-due.days} j de retard`
                                : due.status === "due_today"
                                  ? "Aujourd'hui"
                                  : `Dans ${due.days} j`}
                            </span>
                          </span>
                        ) : (
                          <span className="text-slate-400">Après chaque usage</span>
                        )}
                      </td>
                      <td className="px-5 py-3">
                        <div className="flex items-center justify-end gap-1">
                          <DeclareCleaningDialog
                            plan={{ id: plan.id, name: plan.name }}
                            defaultDate={today}
                            compact
                          />
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
