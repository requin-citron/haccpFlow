"use client";

import { useActionState, useEffect, useState } from "react";

import { declareCleaningAction } from "@/actions/cleaning";
import { AlertIcon, CheckIcon, CloseIcon } from "@/components/icons";
import { INITIAL_CLEANING_RECORD_FORM_STATE } from "@/lib/form-state";
import {
  CANCEL_BUTTON_CLASS,
  FIELD_CLASS,
  ICON_BUTTON_CLASS,
  LABEL_CLASS,
  SUBMIT_BUTTON_CLASS,
} from "@/lib/ui";

export function DeclareCleaningDialog({
  plan,
  defaultDate,
  compact = false,
}: {
  plan: { id: string; name: string };
  defaultDate: string;
  compact?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [state, formAction, pending] = useActionState(
    declareCleaningAction,
    INITIAL_CLEANING_RECORD_FORM_STATE,
  );

  useEffect(() => {
    if (state.status === "success") {
      setOpen(false);
    }
  }, [state]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={
          compact
            ? "inline-flex items-center gap-1.5 rounded-lg bg-teal-600 px-2.5 py-1.5 text-xs font-semibold text-white transition hover:bg-teal-700"
            : "inline-flex items-center gap-2 rounded-xl bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700"
        }
      >
        <CheckIcon className="size-4" />
        {compact ? "Déclarer" : "Déclarer un nettoyage"}
      </button>

      {open ? (
        <div
          role="presentation"
          onClick={() => setOpen(false)}
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/50 p-4 backdrop-blur-sm sm:p-8"
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="declare-cleaning-title"
            onClick={(event) => event.stopPropagation()}
            className="animate-fade-in w-full max-w-md rounded-2xl border border-slate-200 bg-white shadow-xl"
          >
            <header className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
              <div>
                <h2
                  id="declare-cleaning-title"
                  className="text-lg font-semibold tracking-tight text-slate-900"
                >
                  {plan.name}
                </h2>
                <p className="mt-0.5 text-sm text-slate-500">
                  Déclare un nettoyage réalisé.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Fermer"
                className={ICON_BUTTON_CLASS}
              >
                <CloseIcon className="size-5" />
              </button>
            </header>

            <form action={formAction} className="space-y-5 px-6 py-5">
              <input type="hidden" name="plan_id" value={plan.id} />

              <div className="space-y-1.5">
                <label htmlFor="cleaning_date" className={LABEL_CLASS}>
                  Date du nettoyage
                </label>
                <input
                  id="cleaning_date"
                  name="cleaning_date"
                  type="date"
                  required
                  autoFocus
                  defaultValue={defaultDate}
                  className={FIELD_CLASS}
                />
                <p className="text-xs text-slate-500">
                  Tu peux antidater pour rattraper une journée oubliée.
                </p>
              </div>

              <div className="space-y-1.5">
                <label htmlFor="comment" className={LABEL_CLASS}>
                  Commentaire <span className="font-normal text-slate-400">(optionnel)</span>
                </label>
                <textarea
                  id="comment"
                  name="comment"
                  rows={3}
                  maxLength={2000}
                  placeholder="Produit réellement utilisé, remarque…"
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

              <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
                <button type="button" onClick={() => setOpen(false)} className={CANCEL_BUTTON_CLASS}>
                  Annuler
                </button>
                <button type="submit" disabled={pending} className={SUBMIT_BUTTON_CLASS}>
                  {pending ? "Enregistrement…" : "Déclarer"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  );
}
