import Link from "next/link";

import { DeclareCleaningDialog } from "@/components/cleaning/declare-cleaning-dialog";
import {
  NextCleaningCard,
  ScheduleTimeline,
  groupByUrgency,
} from "@/components/cleaning/schedule-timeline";
import { AlertIcon, CheckIcon, DropletIcon, GridIcon } from "@/components/icons";
import { apiFetch } from "@/lib/api";
import { CLEANING_FREQUENCY_LABELS, formatShortDay, todayIso } from "@/lib/format";
import type { CleaningPlan, CleaningScheduleEntry } from "@/lib/types";

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
  const next = schedule[0];
  const perUsePlans = plans.filter((plan) => plan.frequency === "after_each_use");

  let runningRank = 1;
  const groups = groupByUrgency(schedule).map((group) => {
    const startRank = runningRank;
    runningRank += group.entries.length;
    return { ...group, startRank };
  });

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

      {plans.length === 0 ? (
        <section className="rounded-2xl border border-dashed border-slate-300 bg-white/60 px-6 py-16 text-center">
          <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-slate-100 text-slate-500">
            <DropletIcon className="size-6" />
          </span>
          <h2 className="mt-4 text-base font-semibold text-slate-900">Aucun plan défini</h2>
          <p className="mx-auto mt-1 max-w-sm text-sm text-slate-500">
            Commence par créer un plan dans l&apos;onglet « Plan de nettoyage ».
          </p>
          <Link
            href="/cleaning/plans"
            className="mt-6 inline-flex items-center gap-2 rounded-xl bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700"
          >
            Créer un plan
          </Link>
        </section>
      ) : (
        <>
          {next ? <NextCleaningCard entry={next} today={today} /> : null}

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

          <section className="space-y-6">
            <div>
              <h2 className="text-base font-semibold text-slate-900">Dans l&apos;ordre</h2>
              <p className="text-xs text-slate-500">
                Du plus urgent au plus lointain. Déclare un nettoyage quand il est fait, la suite
                se recalcule automatiquement.
              </p>
            </div>

            {groups.length === 0 ? (
              <div className="flex items-center gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-800">
                <CheckIcon className="size-5 shrink-0" />
                Aucun nettoyage planifié : seuls des plans après chaque usage sont actifs.
              </div>
            ) : (
              groups.map((group) => (
                <div key={group.status} className="space-y-3">
                  <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                    {group.title}
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
                      {group.entries.length}
                    </span>
                  </h3>
                  <ScheduleTimeline
                    entries={group.entries}
                    today={today}
                    startRank={group.startRank}
                  />
                </div>
              ))
            )}
          </section>

          {perUsePlans.length > 0 ? (
            <section className="space-y-3">
              <div>
                <h2 className="text-base font-semibold text-slate-900">Après chaque usage</h2>
                <p className="text-xs text-slate-500">
                  Pas d&apos;échéance : à déclarer au fil de l&apos;eau, autant de fois que
                  nécessaire.
                </p>
              </div>
              <ul className="space-y-3">
                {perUsePlans.map((plan) => (
                  <li
                    key={plan.id}
                    className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
                  >
                    <div className="min-w-0 flex-1">
                      <h3 className="truncate font-medium text-slate-900">
                        <Link
                          href={`/cleaning/${plan.id}`}
                          className="transition hover:text-teal-700"
                        >
                          {plan.name}
                        </Link>
                      </h3>
                      <p className="mt-0.5 text-xs text-slate-500">
                        {CLEANING_FREQUENCY_LABELS[plan.frequency]}
                        {plan.last_cleaning_date
                          ? ` · dernier nettoyage le ${formatShortDay(plan.last_cleaning_date)}`
                          : " · jamais nettoyé"}
                      </p>
                      {plan.products ? (
                        <p className="mt-1 text-xs text-slate-500">{plan.products}</p>
                      ) : null}
                    </div>
                    <DeclareCleaningDialog
                      plan={{ id: plan.id, name: plan.name }}
                      defaultDate={today}
                      compact
                    />
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </>
      )}
    </div>
  );
}
