"use client";

import { useActionState, useEffect, useState, useTransition } from "react";

import { deleteCleaningRecordAction, updateCleaningRecordAction } from "@/actions/cleaning";
import { AlertIcon, CloseIcon, PencilIcon, TrashIcon } from "@/components/icons";
import { INITIAL_CLEANING_RECORD_FORM_STATE } from "@/lib/form-state";
import {
  CANCEL_BUTTON_CLASS,
  FIELD_CLASS,
  ICON_BUTTON_CLASS,
  LABEL_CLASS,
  SUBMIT_BUTTON_CLASS,
} from "@/lib/ui";
import type { CleaningRecord } from "@/lib/types";

export function CleaningRecordActions({
  planId,
  record,
}: {
  planId: string;
  record: CleaningRecord;
}) {
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [pending, startTransition] = useTransition();
  const [state, formAction, saving] = useActionState(
    updateCleaningRecordAction,
    INITIAL_CLEANING_RECORD_FORM_STATE,
  );

  useEffect(() => {
    if (state.status === "success") {
      setEditing(false);
    }
  }, [state]);

  return (
    <div className="flex items-center justify-end gap-1">
      <button
        type="button"
        onClick={() => setEditing(true)}
        aria-label="Corriger la déclaration"
        title="Corriger la déclaration"
        className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
      >
        <PencilIcon className="size-4" />
      </button>

      {confirming ? (
        <>
          <button
            type="button"
            disabled={pending}
            onClick={() =>
              startTransition(async () => {
                await deleteCleaningRecordAction(planId, record.id);
              })
            }
            className="rounded-lg bg-rose-600 px-2.5 py-1.5 text-xs font-semibold text-white transition hover:bg-rose-700 disabled:opacity-60"
          >
            {pending ? "Suppression…" : "Confirmer"}
          </button>
          <button
            type="button"
            onClick={() => setConfirming(false)}
            aria-label="Annuler"
            className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
          >
            <CloseIcon className="size-4" />
          </button>
        </>
      ) : (
        <button
          type="button"
          onClick={() => setConfirming(true)}
          aria-label="Supprimer la déclaration"
          title="Supprimer la déclaration"
          className="rounded-lg p-1.5 text-slate-400 transition hover:bg-rose-50 hover:text-rose-600"
        >
          <TrashIcon className="size-4" />
        </button>
      )}

      {editing ? (
        <div
          role="presentation"
          onClick={() => setEditing(false)}
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/50 p-4 text-left backdrop-blur-sm sm:p-8"
        >
          <div
            role="dialog"
            aria-modal="true"
            onClick={(event) => event.stopPropagation()}
            className="animate-fade-in w-full max-w-md rounded-2xl border border-slate-200 bg-white shadow-xl"
          >
            <header className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
              <div>
                <h2 className="text-lg font-semibold tracking-tight text-slate-900">
                  Corriger la déclaration
                </h2>
                <p className="mt-0.5 text-sm text-slate-500">
                  La correction est tracée dans le journal.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setEditing(false)}
                aria-label="Fermer"
                className={ICON_BUTTON_CLASS}
              >
                <CloseIcon className="size-5" />
              </button>
            </header>

            <form action={formAction} className="space-y-5 px-6 py-5">
              <input type="hidden" name="plan_id" value={planId} />
              <input type="hidden" name="record_id" value={record.id} />

              <div className="space-y-1.5">
                <label htmlFor={`cleaning_date_${record.id}`} className={LABEL_CLASS}>
                  Date du nettoyage
                </label>
                <input
                  id={`cleaning_date_${record.id}`}
                  name="cleaning_date"
                  type="date"
                  required
                  defaultValue={record.cleaning_date}
                  className={FIELD_CLASS}
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor={`comment_${record.id}`} className={LABEL_CLASS}>
                  Commentaire <span className="font-normal text-slate-400">(optionnel)</span>
                </label>
                <textarea
                  id={`comment_${record.id}`}
                  name="comment"
                  rows={3}
                  maxLength={2000}
                  defaultValue={record.comment ?? ""}
                  placeholder="Vider un champ efface le commentaire."
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
                <button
                  type="button"
                  onClick={() => setEditing(false)}
                  className={CANCEL_BUTTON_CLASS}
                >
                  Annuler
                </button>
                <button type="submit" disabled={saving} className={SUBMIT_BUTTON_CLASS}>
                  {saving ? "Enregistrement…" : "Enregistrer"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
