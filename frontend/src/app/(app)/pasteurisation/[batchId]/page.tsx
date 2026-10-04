import Link from "next/link";
import { notFound } from "next/navigation";

import { DeleteBatchButton } from "@/components/pasteurisation/delete-batch-button";
import { PasteurisationBatchDialog } from "@/components/pasteurisation/batch-form-dialog";
import { PasteurisationPhaseForm } from "@/components/pasteurisation/phase-form";
import { FlameIcon } from "@/components/icons";
import { ApiError, apiFetch } from "@/lib/api";
import { formatDayLabel, todayIso } from "@/lib/format";
import type { CurrentUser, PasteurisationBatch } from "@/lib/types";

export default async function PasteurisationBatchPage({
  params,
}: {
  params: Promise<{ batchId: string }>;
}) {
  const { batchId } = await params;

  let batch: PasteurisationBatch;
  try {
    batch = await apiFetch<PasteurisationBatch>(`/api/v1/pasteurisations/${batchId}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const user = await apiFetch<CurrentUser>("/api/v1/auth/me");

  return (
    <div className="space-y-8">
      <div>
        <Link
          href="/pasteurisation"
          className="text-sm font-medium text-slate-500 transition hover:text-slate-800"
        >
          ← Retour aux lots de pasteurisation
        </Link>
      </div>

      <header className="flex flex-wrap items-start justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-start gap-4">
          <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-orange-50 text-orange-600">
            <FlameIcon className="size-6" />
          </span>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
              {batch.product_name}
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              Lot <span className="font-mono text-slate-700">{batch.lot_number}</span> ·{" "}
              {batch.quantity} entité{batch.quantity > 1 ? "s" : ""} ·{" "}
              <span className="capitalize">{formatDayLabel(batch.batch_date)}</span>
            </p>
            <p className="mt-2">
              <span
                className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ring-1 ring-inset ${
                  batch.is_complete
                    ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
                    : "bg-amber-50 text-amber-700 ring-amber-200"
                }`}
              >
                {batch.is_complete
                  ? "Trois phases complètes"
                  : `${batch.filled_phases} phase${batch.filled_phases > 1 ? "s" : ""} sur ${batch.phases.length}`}
              </span>
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <PasteurisationBatchDialog batch={batch} defaultDate={todayIso()} />
          {user.role === "admin" ? (
            <DeleteBatchButton id={batch.id} lot={batch.lot_number} />
          ) : null}
        </div>
      </header>

      <section className="space-y-4">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Phases</h2>
          <p className="text-xs text-slate-500">
            Remplis chaque phase quand elle se termine : la durée se calcule à partir des deux
            heures, et chaque correction est journalisée.
          </p>
        </div>

        <div className="space-y-4">
          {batch.phases.map((slot, index) => (
            <PasteurisationPhaseForm
              key={slot.phase}
              batchId={batch.id}
              slot={slot}
              rank={index + 1}
            />
          ))}
        </div>
      </section>
    </div>
  );
}
