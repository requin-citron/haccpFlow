"use client";

import { useActionState, useEffect, useState } from "react";

import { saveTransportReadingsAction } from "@/actions/transport";
import { AlertIcon, CheckIcon } from "@/components/icons";
import { INITIAL_TRANSPORT_FORM_STATE } from "@/lib/form-state";
import { FIELD_CLASS, LABEL_CLASS, SUBMIT_BUTTON_CLASS } from "@/lib/ui";

export function TransportNoteForm({
  transportId,
  observation,
}: {
  transportId: string;
  observation: string | null;
}) {
  const [state, formAction, pending] = useActionState(
    saveTransportReadingsAction,
    INITIAL_TRANSPORT_FORM_STATE,
  );
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (state.status !== "success") {
      return;
    }
    setSaved(true);
    const timer = setTimeout(() => setSaved(false), 3000);
    return () => clearTimeout(timer);
  }, [state]);

  return (
    <form action={formAction} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <input type="hidden" name="transport_id" value={transportId} />

      <div className="space-y-1.5">
        <label htmlFor="observation" className={LABEL_CLASS}>
          Observation <span className="font-normal text-slate-400">(optionnel)</span>
        </label>
        <textarea
          id="observation"
          name="observation"
          rows={3}
          maxLength={2000}
          defaultValue={observation ?? ""}
          placeholder="Écart de température, remarque sur la livraison…"
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
          {pending ? "Enregistrement…" : "Enregistrer l'observation"}
        </button>
      </div>
    </form>
  );
}
