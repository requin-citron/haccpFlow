"use client";

import { useActionState, useEffect, useRef, useState } from "react";

import { createEquipmentAction, updateEquipmentAction } from "@/actions/equipment";
import { AlertIcon, CloseIcon, FridgeIcon, PencilIcon, PlusIcon, SnowflakeIcon } from "@/components/icons";
import { INITIAL_EQUIPMENT_FORM_STATE } from "@/lib/form-state";
import type { Equipment } from "@/lib/types";

const FIELD_CLASS =
  "w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-teal-500 focus:ring-4 focus:ring-teal-500/15";

const LABEL_CLASS = "block text-sm font-medium text-slate-700";

const PRIMARY_TRIGGER_CLASS =
  "inline-flex items-center gap-2 rounded-xl bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700 focus:outline-none focus-visible:ring-4 focus-visible:ring-teal-500/30";

const SECONDARY_TRIGGER_CLASS =
  "inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-100 hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400";

export function EquipmentFormDialog({ equipment }: { equipment?: Equipment }) {
  const isEdit = equipment !== undefined;
  const [open, setOpen] = useState(false);
  const [state, formAction, pending] = useActionState(
    isEdit ? updateEquipmentAction : createEquipmentAction,
    INITIAL_EQUIPMENT_FORM_STATE,
  );
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    if (state.status === "success") {
      formRef.current?.reset();
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
          aria-label={`Modifier ${equipment.name}`}
          className={SECONDARY_TRIGGER_CLASS}
        >
          <PencilIcon className="size-4" />
          Modifier
        </button>
      ) : (
        <button type="button" onClick={() => setOpen(true)} className={PRIMARY_TRIGGER_CLASS}>
          <PlusIcon className="size-4" />
          Ajouter un matériel
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
            aria-labelledby="equipment-form-title"
            onClick={(event) => event.stopPropagation()}
            className="animate-fade-in w-full max-w-lg rounded-2xl border border-slate-200 bg-white shadow-xl"
          >
            <header className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
              <div>
                <h2
                  id="equipment-form-title"
                  className="text-lg font-semibold tracking-tight text-slate-900"
                >
                  {isEdit ? "Modifier le matériel" : "Nouveau matériel"}
                </h2>
                <p className="mt-0.5 text-sm text-slate-500">
                  {isEdit
                    ? "Mets à jour les informations et les seuils réglementaires."
                    : "Déclare une enceinte réfrigérée à surveiller."}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Fermer"
                className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
              >
                <CloseIcon className="size-5" />
              </button>
            </header>

            <form ref={formRef} action={formAction} className="space-y-5 px-6 py-5">
              {isEdit ? <input type="hidden" name="id" value={equipment.id} /> : null}

              <div className="space-y-1.5">
                <label htmlFor="name" className={LABEL_CLASS}>
                  Nom du matériel
                </label>
                <input
                  id="name"
                  name="name"
                  required
                  autoFocus
                  maxLength={120}
                  defaultValue={equipment?.name ?? ""}
                  placeholder="Frigo cuisine"
                  className={FIELD_CLASS}
                />
              </div>

              <fieldset className="space-y-2">
                <legend className={LABEL_CLASS}>Type d&apos;enceinte</legend>
                <div className="grid grid-cols-2 gap-3">
                  <label className="relative cursor-pointer">
                    <input
                      type="radio"
                      name="type"
                      value="fridge"
                      defaultChecked={equipment?.type !== "freezer"}
                      className="peer sr-only"
                    />
                    <span className="flex items-center gap-2.5 rounded-xl border border-slate-300 bg-white px-3.5 py-3 text-sm font-medium text-slate-700 transition peer-checked:border-teal-500 peer-checked:bg-teal-50 peer-checked:text-teal-800 peer-focus-visible:ring-4 peer-focus-visible:ring-teal-500/20">
                      <FridgeIcon className="size-5 shrink-0" />
                      Réfrigérateur
                    </span>
                  </label>
                  <label className="relative cursor-pointer">
                    <input
                      type="radio"
                      name="type"
                      value="freezer"
                      defaultChecked={equipment?.type === "freezer"}
                      className="peer sr-only"
                    />
                    <span className="flex items-center gap-2.5 rounded-xl border border-slate-300 bg-white px-3.5 py-3 text-sm font-medium text-slate-700 transition peer-checked:border-teal-500 peer-checked:bg-teal-50 peer-checked:text-teal-800 peer-focus-visible:ring-4 peer-focus-visible:ring-teal-500/20">
                      <SnowflakeIcon className="size-5 shrink-0" />
                      Congélateur
                    </span>
                  </label>
                </div>
              </fieldset>

              <fieldset className="space-y-2">
                <legend className={LABEL_CLASS}>Seuils de température (°C)</legend>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <label htmlFor="min_temperature_celsius" className="text-xs text-slate-500">
                      Minimum
                    </label>
                    <input
                      id="min_temperature_celsius"
                      name="min_temperature_celsius"
                      type="number"
                      step="0.5"
                      inputMode="decimal"
                      defaultValue={equipment?.min_temperature_celsius ?? ""}
                      placeholder="0"
                      className={FIELD_CLASS}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label htmlFor="max_temperature_celsius" className="text-xs text-slate-500">
                      Maximum
                    </label>
                    <input
                      id="max_temperature_celsius"
                      name="max_temperature_celsius"
                      type="number"
                      step="0.5"
                      inputMode="decimal"
                      defaultValue={equipment?.max_temperature_celsius ?? ""}
                      placeholder="4"
                      className={FIELD_CLASS}
                    />
                  </div>
                </div>
                <p className="text-xs text-slate-500">
                  Laisse les deux vides pour appliquer les seuils par défaut configurés sur le
                  serveur.
                </p>
              </fieldset>

              <div className="space-y-1.5">
                <label htmlFor="location" className={LABEL_CLASS}>
                  Emplacement <span className="font-normal text-slate-400">(optionnel)</span>
                </label>
                <input
                  id="location"
                  name="location"
                  maxLength={120}
                  defaultValue={equipment?.location ?? ""}
                  placeholder="Cuisine, réserve…"
                  className={FIELD_CLASS}
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="notes" className={LABEL_CLASS}>
                  Notes <span className="font-normal text-slate-400">(optionnel)</span>
                </label>
                <textarea
                  id="notes"
                  name="notes"
                  rows={3}
                  maxLength={2000}
                  defaultValue={equipment?.notes ?? ""}
                  placeholder="Sous le plan de travail, à côté de la chambre froide…"
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
                  onClick={() => setOpen(false)}
                  className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  disabled={pending}
                  className="rounded-xl bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {pending ? "Enregistrement…" : isEdit ? "Enregistrer" : "Créer le matériel"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  );
}
