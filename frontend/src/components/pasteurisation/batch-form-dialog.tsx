"use client";

import { useActionState, useEffect, useState } from "react";

import {
  createPasteurisationAction,
  updatePasteurisationAction,
} from "@/actions/pasteurisation";
import { AlertIcon, CloseIcon, PencilIcon, PlusIcon } from "@/components/icons";
import { INITIAL_PASTEURISATION_FORM_STATE } from "@/lib/form-state";
import {
  CANCEL_BUTTON_CLASS,
  FIELD_CLASS,
  ICON_BUTTON_CLASS,
  LABEL_CLASS,
  PRIMARY_TRIGGER_CLASS,
  SECONDARY_TRIGGER_CLASS,
  SUBMIT_BUTTON_CLASS,
} from "@/lib/ui";
import type { PasteurisationBatch } from "@/lib/types";

export function PasteurisationBatchDialog({
  batch,
  defaultDate,
}: {
  batch?: PasteurisationBatch;
  defaultDate: string;
}) {
  const isEdit = batch !== undefined;
  const [open, setOpen] = useState(false);
  const [state, formAction, pending] = useActionState(
    isEdit ? updatePasteurisationAction : createPasteurisationAction,
    INITIAL_PASTEURISATION_FORM_STATE,
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
      {isEdit ? (
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label={`Modifier le lot ${batch.lot_number}`}
          className={SECONDARY_TRIGGER_CLASS}
        >
          <PencilIcon className="size-4" />
          Modifier
        </button>
      ) : (
        <button type="button" onClick={() => setOpen(true)} className={PRIMARY_TRIGGER_CLASS}>
          <PlusIcon className="size-4" />
          Nouveau lot
        </button>
      )}

      {open ? (
        <div
          role="presentation"
          onClick={() => setOpen(false)}
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/50 p-4 backdrop-blur-sm sm:p-8"
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="pasteurisation-form-title"
            onClick={(event) => event.stopPropagation()}
            className="animate-fade-in w-full max-w-lg rounded-2xl border border-slate-200 bg-white shadow-xl"
          >
            <header className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
              <div>
                <h2
                  id="pasteurisation-form-title"
                  className="text-lg font-semibold tracking-tight text-slate-900"
                >
                  {isEdit ? "Modifier le lot" : "Nouveau lot de pasteurisation"}
                </h2>
                <p className="mt-0.5 text-sm text-slate-500">
                  Les trois phases se remplissent ensuite, au fil de la production.
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
              {isEdit ? <input type="hidden" name="id" value={batch.id} /> : null}

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label htmlFor="batch_date" className={LABEL_CLASS}>
                    Date
                  </label>
                  <input
                    id="batch_date"
                    name="batch_date"
                    type="date"
                    required
                    defaultValue={batch?.batch_date ?? defaultDate}
                    className={FIELD_CLASS}
                  />
                </div>
                <div className="space-y-1.5">
                  <label htmlFor="quantity" className={LABEL_CLASS}>
                    Nombre d&apos;entités
                  </label>
                  <input
                    id="quantity"
                    name="quantity"
                    type="number"
                    min={1}
                    step={1}
                    required
                    defaultValue={batch?.quantity ?? ""}
                    placeholder="120"
                    className={FIELD_CLASS}
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label htmlFor="product_name" className={LABEL_CLASS}>
                  Nom du produit
                </label>
                <input
                  id="product_name"
                  name="product_name"
                  required
                  maxLength={160}
                  autoFocus
                  defaultValue={batch?.product_name ?? ""}
                  placeholder="Crème anglaise"
                  className={FIELD_CLASS}
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="lot_number" className={LABEL_CLASS}>
                  Numéro de lot
                </label>
                <input
                  id="lot_number"
                  name="lot_number"
                  required
                  maxLength={80}
                  defaultValue={batch?.lot_number ?? ""}
                  placeholder="LOT-2026-014"
                  className={FIELD_CLASS}
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
                  {pending ? "Enregistrement…" : isEdit ? "Enregistrer" : "Créer le lot"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  );
}
