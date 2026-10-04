"use client";

import { useActionState, useEffect, useState } from "react";

import { savePasteurisationPhaseAction } from "@/actions/pasteurisation";
import { AlertIcon, CheckIcon } from "@/components/icons";
import { INITIAL_PASTEURISATION_FORM_STATE } from "@/lib/form-state";
import {
  PASTEURISATION_PHASE_LABELS,
  formatDuration,
  formatTimeInput,
} from "@/lib/format";
import {
  PHASE_STATE_ACCENTS,
  PHASE_STATE_BADGES,
  PHASE_STATE_LABELS,
  phaseState,
} from "@/lib/pasteurisation";
import { FIELD_CLASS, LABEL_CLASS, SUBMIT_BUTTON_CLASS } from "@/lib/ui";
import type { PasteurisationPhaseSlot } from "@/lib/types";

export function PasteurisationPhaseForm({
  batchId,
  slot,
  rank,
}: {
  batchId: string;
  slot: PasteurisationPhaseSlot;
  rank: number;
}) {
  const [state, formAction, pending] = useActionState(
    savePasteurisationPhaseAction,
    INITIAL_PASTEURISATION_FORM_STATE,
  );
  const [saved, setSaved] = useState(false);
  const current = phaseState(slot);

  useEffect(() => {
    if (state.status !== "success") {
      return;
    }
    setSaved(true);
    const timer = setTimeout(() => setSaved(false), 3000);
    return () => clearTimeout(timer);
  }, [state]);

  return (
    <form
      action={formAction}
      className={`space-y-4 rounded-2xl border bg-white p-5 shadow-sm ${PHASE_STATE_ACCENTS[current]}`}
    >
      <input type="hidden" name="batch_id" value={batchId} />
      <input type="hidden" name="phase" value={slot.phase} />

      <header className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="flex items-center gap-2 font-semibold text-slate-900">
          <span className="grid size-7 place-items-center rounded-full bg-slate-100 text-xs font-semibold tabular-nums text-slate-600">
            {rank}
          </span>
          {PASTEURISATION_PHASE_LABELS[slot.phase]}
        </h3>
        <span
          className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ring-1 ring-inset ${PHASE_STATE_BADGES[current]}`}
        >
          {PHASE_STATE_LABELS[current]}
        </span>
      </header>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="space-y-1.5">
          <label htmlFor={`started_at_${slot.phase}`} className={LABEL_CLASS}>
            Heure de début
          </label>
          <input
            id={`started_at_${slot.phase}`}
            name="started_at"
            type="time"
            defaultValue={formatTimeInput(slot.started_at)}
            className={FIELD_CLASS}
          />
        </div>
        <div className="space-y-1.5">
          <label htmlFor={`ended_at_${slot.phase}`} className={LABEL_CLASS}>
            Heure de fin
          </label>
          <input
            id={`ended_at_${slot.phase}`}
            name="ended_at"
            type="time"
            defaultValue={formatTimeInput(slot.ended_at)}
            className={FIELD_CLASS}
          />
        </div>
        <div className="space-y-1.5">
          <label htmlFor={`target_${slot.phase}`} className={LABEL_CLASS}>
            Température cible (°C)
          </label>
          <input
            id={`target_${slot.phase}`}
            name="target_temperature_celsius"
            type="number"
            step="0.5"
            inputMode="decimal"
            defaultValue={slot.target_temperature_celsius ?? ""}
            placeholder="85"
            className={FIELD_CLASS}
          />
        </div>
      </div>

      <p className="text-xs text-slate-500">
        Durée calculée :{" "}
        <span className="font-medium text-slate-700">
          {formatDuration(slot.duration_minutes)}
        </span>
      </p>

      <div className="space-y-1.5">
        <label htmlFor={`observation_${slot.phase}`} className={LABEL_CLASS}>
          Observation <span className="font-normal text-slate-400">(optionnel)</span>
        </label>
        <textarea
          id={`observation_${slot.phase}`}
          name="observation"
          rows={2}
          maxLength={2000}
          defaultValue={slot.observation ?? ""}
          placeholder="Remarque sur la phase…"
          className={`${FIELD_CLASS} resize-none`}
        />
      </div>

      {state.status === "error" && state.message ? (
        <p
          role="alert"
          className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-sm text-rose-700"
        >
          <AlertIcon className="mt-0.5 size-4 shrink-0" />
          <span>{state.message}</span>
        </p>
      ) : null}

      <div className="flex items-center justify-end gap-3">
        {saved ? (
          <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-700">
            <CheckIcon className="size-4" />
            Enregistré
          </span>
        ) : null}
        <button type="submit" disabled={pending} className={SUBMIT_BUTTON_CLASS}>
          {pending ? "Enregistrement…" : "Enregistrer la phase"}
        </button>
      </div>

    </form>
  );
}
