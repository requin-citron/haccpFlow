"use client";

import { useActionState, useEffect, useState } from "react";

import { createVehicleAction, updateVehicleAction } from "@/actions/vehicles";
import { AlertIcon, CloseIcon, PencilIcon, PlusIcon } from "@/components/icons";
import { useI18n } from "@/components/locale-provider";
import { INITIAL_VEHICLE_FORM_STATE } from "@/lib/form-state";
import {
  CANCEL_BUTTON_CLASS,
  FIELD_CLASS,
  ICON_BUTTON_CLASS,
  LABEL_CLASS,
  PRIMARY_TRIGGER_CLASS,
  SECONDARY_TRIGGER_CLASS,
  SUBMIT_BUTTON_CLASS,
} from "@/lib/ui";
import type { Vehicle } from "@/lib/types";

export function VehicleFormDialog({ vehicle }: { vehicle?: Vehicle }) {
  const { t } = useI18n();
  const isEdit = vehicle !== undefined;
  const [open, setOpen] = useState(false);
  const [state, formAction, pending] = useActionState(
    isEdit ? updateVehicleAction : createVehicleAction,
    INITIAL_VEHICLE_FORM_STATE,
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
          aria-label={t("Modifier {name}", { name: vehicle.name ?? vehicle.plate ?? "" })}
          className={SECONDARY_TRIGGER_CLASS}
        >
          <PencilIcon className="size-4" />
          {t("Modifier")}
        </button>
      ) : (
        <button type="button" onClick={() => setOpen(true)} className={PRIMARY_TRIGGER_CLASS}>
          <PlusIcon className="size-4" />
          {t("Nouveau véhicule")}
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
            aria-labelledby="vehicle-form-title"
            onClick={(event) => event.stopPropagation()}
            className="animate-fade-in w-full max-w-md rounded-2xl border border-slate-200 bg-white shadow-xl"
          >
            <header className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
              <div>
                <h2
                  id="vehicle-form-title"
                  className="text-lg font-semibold tracking-tight text-slate-900"
                >
                  {isEdit ? t("Modifier le véhicule") : t("Nouveau véhicule")}
                </h2>
                <p className="mt-0.5 text-sm text-slate-500">
                  {t("Utilisé ensuite pour déclarer les transports.")}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label={t("Fermer")}
                className={ICON_BUTTON_CLASS}
              >
                <CloseIcon className="size-5" />
              </button>
            </header>

            <form action={formAction} className="space-y-5 px-6 py-5">
              {isEdit ? <input type="hidden" name="id" value={vehicle.id} /> : null}

              <div className="space-y-1.5">
                <label htmlFor="name" className={LABEL_CLASS}>
                  {t("Nom du véhicule")}
                </label>
                <input
                  id="name"
                  name="name"
                  maxLength={120}
                  autoFocus
                  defaultValue={vehicle?.name ?? ""}
                  placeholder={t("Camion frigo 1")}
                  className={FIELD_CLASS}
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="plate" className={LABEL_CLASS}>
                  {t("Numéro de plaque")}
                </label>
                <input
                  id="plate"
                  name="plate"
                  maxLength={32}
                  defaultValue={vehicle?.plate ?? ""}
                  placeholder="AB-123-CD"
                  className={FIELD_CLASS}
                />
                <p className="text-xs text-slate-500">
                  {t(
                    "Renseigne au moins l'un des deux. Un nom et une plaque ne peuvent pas être réutilisés par un autre véhicule actif.",
                  )}
                </p>
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
                  {t("Annuler")}
                </button>
                <button type="submit" disabled={pending} className={SUBMIT_BUTTON_CLASS}>
                  {pending
                    ? t("Enregistrement…")
                    : isEdit
                      ? t("Enregistrer")
                      : t("Créer le véhicule")}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  );
}
