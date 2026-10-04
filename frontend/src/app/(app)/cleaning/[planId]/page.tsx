import Link from "next/link";
import { notFound } from "next/navigation";

import { DeclareCleaningDialog } from "@/components/cleaning/declare-cleaning-dialog";
import { DeletePlanButton } from "@/components/cleaning/delete-plan-button";
import { CleaningPlanDialog } from "@/components/cleaning/plan-form-dialog";
import { CleaningRecordActions } from "@/components/cleaning/record-actions";
import { DropletIcon } from "@/components/icons";
import { apiFetch } from "@/lib/api";
import {
  CLEANING_FREQUENCY_LABELS,
  formatDateTimeUtc,
  formatShortDay,
  todayIso,
} from "@/lib/format";
import type { CleaningPlan, CleaningRecord, CurrentUser } from "@/lib/types";

const RECENT_LIMIT = 20;

export default async function CleaningPlanDetailPage({
  params,
}: {
  params: Promise<{ planId: string }>;
}) {
  const { planId } = await params;
  const today = todayIso();

  const [user, plans] = await Promise.all([
    apiFetch<CurrentUser>("/api/v1/auth/me"),
    apiFetch<CleaningPlan[]>("/api/v1/cleaning-plans"),
  ]);
  const plan = plans.find((item) => item.id === planId);
  if (!plan) {
    notFound();
  }

  const records = await apiFetch<CleaningRecord[]>(`/api/v1/cleaning-plans/${plan.id}/records`);
  const recent = records.slice(0, RECENT_LIMIT);

  return (
    <div className="space-y-8">
      <div>
        <Link
          href="/cleaning/plans"
          className="text-sm font-medium text-slate-500 transition hover:text-slate-800"
        >
          ← Retour aux plans de nettoyage
        </Link>
      </div>

      <header className="flex flex-wrap items-start justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-start gap-4">
          <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-teal-50 text-teal-600">
            <DropletIcon className="size-6" />
          </span>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{plan.name}</h1>
            <p className="mt-1 text-sm text-slate-500">
              {CLEANING_FREQUENCY_LABELS[plan.frequency]}
              {plan.last_cleaning_date
                ? ` · dernier nettoyage le ${formatShortDay(plan.last_cleaning_date)}`
                : " · jamais nettoyé"}
              {plan.next_due_date
                ? ` · prochaine échéance le ${formatShortDay(plan.next_due_date)}`
                : ""}
            </p>
            {plan.products ? (
              <p className="mt-2 max-w-xl text-sm text-slate-500">
                <span className="font-medium text-slate-700">Produits :</span> {plan.products}
              </p>
            ) : null}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <DeclareCleaningDialog plan={{ id: plan.id, name: plan.name }} defaultDate={today} />
          <CleaningPlanDialog plan={plan} />
          {user.role === "admin" ? <DeletePlanButton id={plan.id} name={plan.name} /> : null}
        </div>
      </header>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <header className="border-b border-slate-100 px-5 py-4">
          <h2 className="text-base font-semibold text-slate-900">Nettoyages déclarés</h2>
          <p className="text-xs text-slate-500">
            {records.length === 0
              ? "Aucune déclaration pour ce plan."
              : `${records.length} déclaration${records.length > 1 ? "s" : ""}${
                  records.length > RECENT_LIMIT ? `, ${RECENT_LIMIT} plus récentes affichées` : ""
                }. Les corrections sont visibles dans l'onglet Historique.`}
          </p>
        </header>

        {recent.length === 0 ? (
          <div className="px-6 py-12 text-center text-sm text-slate-500">
            Déclare un premier nettoyage pour alimenter l&apos;historique.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[44rem] text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-left text-[11px] uppercase tracking-wide text-slate-500">
                  <th className="px-5 py-3 font-medium">Date du nettoyage</th>
                  <th className="px-5 py-3 font-medium">Commentaire</th>
                  <th className="px-5 py-3 font-medium">Déclaré par</th>
                  <th className="px-5 py-3 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {recent.map((record) => (
                  <tr key={record.id} className="align-top">
                    <td className="whitespace-nowrap px-5 py-3 font-medium text-slate-800">
                      {formatShortDay(record.cleaning_date)}
                    </td>
                    <td className="max-w-[18rem] px-5 py-3 text-slate-500">
                      {record.comment ?? "—"}
                    </td>
                    <td className="px-5 py-3 text-slate-500">
                      {record.performed_by_email ?? "—"}
                      <br />
                      <span className="text-[11px] text-slate-400">
                        {formatDateTimeUtc(record.recorded_at)}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <CleaningRecordActions planId={plan.id} record={record} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
