"use client";

import { useActionState, useEffect, useState } from "react";

import { closeCashSessionAction } from "@/actions/cash-sessions";
import { DenominationFields } from "@/components/cash-sessions/denomination-fields";
import { AlertIcon } from "@/components/icons";
import { countsDraft, draftTotalCents, type CountsDraft } from "@/lib/cash-session";
import { INITIAL_CASH_SESSION_FORM_STATE } from "@/lib/form-state";
import { formatEuros } from "@/lib/format";
import { SUBMIT_BUTTON_CLASS } from "@/lib/ui";

export function CloseSessionForm({ sessionId }: { sessionId: string }) {
  const [draft, setDraft] = useState<CountsDraft>(() => countsDraft());
  const [confirming, setConfirming] = useState(false);
  const [state, formAction, pending] = useActionState(
    closeCashSessionAction,
    INITIAL_CASH_SESSION_FORM_STATE,
  );

  useEffect(() => {
    if (state.status === "success") {
      setConfirming(false);
      setDraft(countsDraft());
    }
  }, [state]);

  const total = draftTotalCents(draft);

  return (
    <form action={formAction} className="space-y-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <input type="hidden" name="session_id" value={sessionId} />

      <div>
        <h3 className="font-semibold text-slate-900">Clôturer le suivi</h3>
        <p className="mt-0.5 text-xs text-slate-500">
          Recompte le contenu de la caisse : ce comptage remplace l&apos;état enregistré et le
          suivi devient définitif. Laisser une coupure vide revient à zéro.
        </p>
      </div>

      <DenominationFields
        draft={draft}
        idPrefix="close_"
        onChange={(field, value) => setDraft((current) => ({ ...current, [field]: value }))}
      />

      <p className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
        Total recompté :{" "}
        <span className="text-base font-semibold tabular-nums text-slate-900">
          {formatEuros(total)}
        </span>
      </p>

      {state.status === "error" && state.message ? (
        <p
          role="alert"
          className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-sm text-rose-700"
        >
          <AlertIcon className="mt-0.5 size-4 shrink-0" />
          <span>{state.message}</span>
        </p>
      ) : null}

      <div className="flex flex-wrap items-center justify-end gap-2 border-t border-slate-100 pt-4">
        {confirming ? (
          <>
            <button
              type="button"
              onClick={() => setConfirming(false)}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
            >
              Annuler
            </button>
            <button type="submit" disabled={pending} className={SUBMIT_BUTTON_CLASS}>
              {pending ? "Clôture…" : `Confirmer ${formatEuros(total)}`}
            </button>
          </>
        ) : (
          <button
            type="button"
            onClick={() => setConfirming(true)}
            className={SUBMIT_BUTTON_CLASS}
          >
            Clôturer le suivi
          </button>
        )}
      </div>
    </form>
  );
}
