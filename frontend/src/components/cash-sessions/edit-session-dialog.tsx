"use client";

import { useActionState, useEffect, useState } from "react";

import { updateCashSessionAction } from "@/actions/cash-sessions";
import { DenominationFields } from "@/components/cash-sessions/denomination-fields";
import { AlertIcon, CloseIcon, PencilIcon } from "@/components/icons";
import { countsDraft, draftTotalCents, type CountsDraft } from "@/lib/cash-session";
import { INITIAL_CASH_SESSION_FORM_STATE } from "@/lib/form-state";
import { formatEuros } from "@/lib/format";
import {
  CANCEL_BUTTON_CLASS,
  FIELD_CLASS,
  ICON_BUTTON_CLASS,
  LABEL_CLASS,
  SECONDARY_TRIGGER_CLASS,
  SUBMIT_BUTTON_CLASS,
} from "@/lib/ui";
import type { CashSession } from "@/lib/types";

/** Corrects the date or the opening float of a session that is still open. */
export function EditSessionDialog({ session }: { session: CashSession }) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<CountsDraft>(() => countsDraft(session.opening_counts));
  const [state, formAction, pending] = useActionState(
    updateCashSessionAction,
    INITIAL_CASH_SESSION_FORM_STATE,
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
        onClick={() => {
          setDraft(countsDraft(session.opening_counts));
          setOpen(true);
        }}
        className={SECONDARY_TRIGGER_CLASS}
      >
        <PencilIcon className="size-4" />
        Modifier
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
            aria-labelledby="edit-session-title"
            onClick={(event) => event.stopPropagation()}
            className="animate-fade-in w-full max-w-lg rounded-2xl border border-slate-200 bg-white shadow-xl"
          >
            <header className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
              <div>
                <h2
                  id="edit-session-title"
                  className="text-lg font-semibold tracking-tight text-slate-900"
                >
                  Corriger le suivi
                </h2>
                <p className="mt-0.5 text-sm text-slate-500">
                  La date et le fond de caisse restent modifiables tant que le suivi est ouvert.
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
              <input type="hidden" name="session_id" value={session.id} />

              <div className="space-y-1.5">
                <label htmlFor="session_date_edit" className={LABEL_CLASS}>
                  Date du suivi
                </label>
                <input
                  id="session_date_edit"
                  name="session_date"
                  type="date"
                  required
                  defaultValue={session.session_date}
                  className={FIELD_CLASS}
                />
              </div>

              <DenominationFields
                draft={draft}
                idPrefix="edit_"
                onChange={(field, value) => setDraft((current) => ({ ...current, [field]: value }))}
              />

              <p className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
                Fond de caisse :{" "}
                <span className="text-base font-semibold tabular-nums text-slate-900">
                  {formatEuros(draftTotalCents(draft))}
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

              <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
                <button type="button" onClick={() => setOpen(false)} className={CANCEL_BUTTON_CLASS}>
                  Annuler
                </button>
                <button type="submit" disabled={pending} className={SUBMIT_BUTTON_CLASS}>
                  {pending ? "Enregistrement…" : "Enregistrer"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  );
}
