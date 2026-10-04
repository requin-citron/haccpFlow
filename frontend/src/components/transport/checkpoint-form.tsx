"use client";

import { useActionState, useEffect, useState } from "react";

import { saveTransportReadingsAction } from "@/actions/transport";
import { AlertIcon, CheckIcon } from "@/components/icons";
import { INITIAL_TRANSPORT_FORM_STATE } from "@/lib/form-state";
import { formatTimeInput } from "@/lib/format";
import { STATUS_ACCENTS, STATUS_BADGES, STATUS_LABELS } from "@/lib/status";
import { checkpointState } from "@/lib/transport";
import { FIELD_CLASS, LABEL_CLASS, SUBMIT_BUTTON_CLASS } from "@/lib/ui";

export function TransportCheckpointForm({
  transportId,
  kind,
  title,
  rank,
  time,
  temperature,
}: {
  transportId: string;
  /** Drives the field names sent to the API. */
  kind: "departure" | "arrival";
  title: string;
  rank: number;
  time: string | null;
  temperature: number | null;
}) {
  const [state, formAction, pending] = useActionState(
    saveTransportReadingsAction,
    INITIAL_TRANSPORT_FORM_STATE,
  );
  const [saved, setSaved] = useState(false);
  const current = checkpointState(time, temperature);

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
      className={`space-y-4 rounded-2xl border bg-white p-5 shadow-sm ${STATUS_ACCENTS[current]}`}
    >
      <input type="hidden" name="transport_id" value={transportId} />

      <header className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="flex items-center gap-2 font-semibold text-slate-900">
          <span className="grid size-7 place-items-center rounded-full bg-slate-100 text-xs font-semibold tabular-nums text-slate-600">
            {rank}
          </span>
          {title}
        </h3>
        <span
          className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ring-1 ring-inset ${STATUS_BADGES[current]}`}
        >
          {STATUS_LABELS[current]}
        </span>
      </header>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <label htmlFor={`${kind}_time`} className={LABEL_CLASS}>
            Heure
          </label>
          <input
            id={`${kind}_time`}
            name={`${kind}_time`}
            type="time"
            defaultValue={formatTimeInput(time)}
            className={FIELD_CLASS}
          />
        </div>
        <div className="space-y-1.5">
          <label htmlFor={`${kind}_temperature_celsius`} className={LABEL_CLASS}>
            Température (°C)
          </label>
          <input
            id={`${kind}_temperature_celsius`}
            name={`${kind}_temperature_celsius`}
            type="number"
            step="0.5"
            inputMode="decimal"
            defaultValue={temperature ?? ""}
            placeholder="4"
            className={FIELD_CLASS}
          />
        </div>
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
          {pending ? "Enregistrement…" : "Enregistrer"}
        </button>
      </div>
    </form>
  );
}
