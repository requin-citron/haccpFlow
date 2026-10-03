"use client";

import { useActionState, useEffect, useState } from "react";

import { createCleaningPlanAction, updateCleaningPlanAction } from "@/actions/cleaning";
import { AlertIcon, CloseIcon, PencilIcon, PlusIcon } from "@/components/icons";
import { INITIAL_CLEANING_PLAN_FORM_STATE } from "@/lib/form-state";
import { CLEANING_FREQUENCY_LABELS } from "@/lib/format";
import {
  CANCEL_BUTTON_CLASS,
  FIELD_CLASS,
  ICON_BUTTON_CLASS,
  LABEL_CLASS,
  PRIMARY_TRIGGER_CLASS,
  SECONDARY_TRIGGER_CLASS,
  SUBMIT_BUTTON_CLASS,
} from "@/lib/ui";
import type { CleaningFrequency, CleaningPlan } from "@/lib/types";

const FREQUENCIES: CleaningFrequency[] = ["after_each_use", "daily", "weekly"];

export function CleaningPlanDialog({ plan }: { plan?: CleaningPlan }) {
  const isEdit = plan !== undefined;
  const [open, setOpen] = useState(false);
  const [state, formAction, pending] = useActionState(
    isEdit ? updateCleaningPlanAction : createCleaningPlanAction,
    INITIAL_CLEANING_PLAN_FORM_STATE,
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
          aria-label={`Modifier ${plan.name}`}
          className={SECONDARY_TRIGGER_CLASS}
        >
          <PencilIcon className="size-4" />
          Modifier
        </button>
      ) : (
        <button type="button" onClick={() => setOpen(true)} className={PRIMARY_TRIGGER_CLASS}>
          <PlusIcon className="size-4" />
          Nouveau plan
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
            aria-labelledby="cleaning-plan-form-title"
            onClick={(event) => event.stopPropagation()}
            className="animate-fade-in w-full max-w-lg rounded-2xl border border-slate-200 bg-white shadow-xl"
          >
            <header className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
              <div>
                <h2
                  id="cleaning-plan-form-title"
                  className="text-lg font-semibold tracking-tight text-slate-900"
                >
                  {isEdit ? "Modifier le plan" : "Nouveau plan de nettoyage"}
                </h2>
                <p className="mt-0.5 text-sm text-slate-500">
                  Une zone ou un matériel, sa fréquence et les produits à utiliser.
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
              {isEdit ? <input type="hidden" name="id" value={plan.id} /> : null}

              <div className="space-y-1.5">
                <label htmlFor="name" className={LABEL_CLASS}>
                  Zone ou matériel
                </label>
                <input
                  id="name"
                  name="name"
                  required
                  autoFocus
                  maxLength={120}
                  defaultValue={plan?.name ?? ""}
                  placeholder="Zone de préparation"
                  className={FIELD_CLASS}
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="frequency" className={LABEL_CLASS}>
                  Fréquence
                </label>
                <select
                  id="frequency"
                  name="frequency"
                  defaultValue={plan?.frequency ?? "daily"}
                  className={FIELD_CLASS}
                >
                  {FREQUENCIES.map((frequency) => (
                    <option key={frequency} value={frequency}>
                      {CLEANING_FREQUENCY_LABELS[frequency]}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-slate-500">
                  Un nettoyage après chaque usage n&apos;apparaît pas dans le prévisionnel : il se
                  déclare au fil de l&apos;eau.
                </p>
              </div>

              <div className="space-y-1.5">
                <label htmlFor="products" className={LABEL_CLASS}>
                  Produits à utiliser{" "}
                  <span className="font-normal text-slate-400">(optionnel)</span>
                </label>
                <textarea
                  id="products"
                  name="products"
                  rows={3}
                  maxLength={1000}
                  defaultValue={plan?.products ?? ""}
                  placeholder="Détergent alimentaire, javel diluée à 0,5 %…"
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
                  {pending ? "Enregistrement…" : isEdit ? "Enregistrer" : "Créer le plan"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  );
}
