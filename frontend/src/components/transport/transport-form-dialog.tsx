"use client";

import { useActionState, useEffect, useState } from "react";

import { createTransportAction, updateTransportAction } from "@/actions/transport";
import { AlertIcon, CloseIcon, PencilIcon, PlusIcon } from "@/components/icons";
import { INITIAL_TRANSPORT_FORM_STATE } from "@/lib/form-state";
import {
  CANCEL_BUTTON_CLASS,
  FIELD_CLASS,
  ICON_BUTTON_CLASS,
  LABEL_CLASS,
  PRIMARY_TRIGGER_CLASS,
  SECONDARY_TRIGGER_CLASS,
  SUBMIT_BUTTON_CLASS,
} from "@/lib/ui";
import type { Transport, Vehicle } from "@/lib/types";

function vehicleLabel(vehicle: Vehicle): string {
  if (vehicle.name && vehicle.plate) {
    return `${vehicle.name} — ${vehicle.plate}`;
  }
  return vehicle.name ?? vehicle.plate ?? "Véhicule";
}

export function TransportFormDialog({
  vehicles,
  transport,
  defaultDate,
}: {
  vehicles: Vehicle[];
  transport?: Transport;
  defaultDate: string;
}) {
  const isEdit = transport !== undefined;
  const initialChoice = transport?.vehicle.id ?? vehicles[0]?.id ?? "external";
  const [open, setOpen] = useState(false);
  const [isExternal, setIsExternal] = useState(initialChoice === "external");
  const [state, formAction, pending] = useActionState(
    isEdit ? updateTransportAction : createTransportAction,
    INITIAL_TRANSPORT_FORM_STATE,
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
          aria-label={`Modifier le transport ${transport.product_name}`}
          className={SECONDARY_TRIGGER_CLASS}
        >
          <PencilIcon className="size-4" />
          Modifier
        </button>
      ) : (
        <button type="button" onClick={() => setOpen(true)} className={PRIMARY_TRIGGER_CLASS}>
          <PlusIcon className="size-4" />
          Nouveau transport
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
            aria-labelledby="transport-form-title"
            onClick={(event) => event.stopPropagation()}
            className="animate-fade-in w-full max-w-lg rounded-2xl border border-slate-200 bg-white shadow-xl"
          >
            <header className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
              <div>
                <h2
                  id="transport-form-title"
                  className="text-lg font-semibold tracking-tight text-slate-900"
                >
                  {isEdit ? "Modifier le transport" : "Nouveau transport"}
                </h2>
                <p className="mt-0.5 text-sm text-slate-500">
                  {isEdit
                    ? "Les relevés de température ne sont pas touchés."
                    : "Les températures de départ et d'arrivée se saisissent ensuite, sur la fiche du transport."}
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
              {isEdit ? <input type="hidden" name="id" value={transport.id} /> : null}

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label htmlFor="transport_date" className={LABEL_CLASS}>
                    Date
                  </label>
                  <input
                    id="transport_date"
                    name="transport_date"
                    type="date"
                    required
                    defaultValue={transport?.transport_date ?? defaultDate}
                    className={FIELD_CLASS}
                  />
                </div>
                <div className="space-y-1.5">
                  <label htmlFor="lot_number" className={LABEL_CLASS}>
                    N° de lot <span className="font-normal text-slate-400">(optionnel)</span>
                  </label>
                  <input
                    id="lot_number"
                    name="lot_number"
                    maxLength={80}
                    defaultValue={transport?.lot_number ?? ""}
                    placeholder="LOT-2026-100"
                    className={FIELD_CLASS}
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label htmlFor="product_name" className={LABEL_CLASS}>
                  Produit transporté
                </label>
                <input
                  id="product_name"
                  name="product_name"
                  required
                  maxLength={160}
                  autoFocus
                  defaultValue={transport?.product_name ?? ""}
                  placeholder="Crème anglaise"
                  className={FIELD_CLASS}
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="place" className={LABEL_CLASS}>
                  Lieu de livraison
                </label>
                <input
                  id="place"
                  name="place"
                  required
                  maxLength={160}
                  defaultValue={transport?.place ?? ""}
                  placeholder="Boulangerie Martin"
                  className={FIELD_CLASS}
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="vehicle_choice" className={LABEL_CLASS}>
                  Véhicule
                </label>
                <select
                  id="vehicle_choice"
                  name="vehicle_choice"
                  defaultValue={initialChoice}
                  onChange={(event) => setIsExternal(event.target.value === "external")}
                  className={FIELD_CLASS}
                >
                  {vehicles.map((vehicle) => (
                    <option key={vehicle.id} value={vehicle.id}>
                      {vehicleLabel(vehicle)}
                    </option>
                  ))}
                  <option value="external">Autre véhicule (non référencé)…</option>
                </select>
                {vehicles.length === 0 ? (
                  <p className="text-xs text-amber-700">
                    Aucun véhicule au référentiel : précise-le à la main, ou ajoute-le depuis la
                    page Matériel.
                  </p>
                ) : null}
              </div>

              {isExternal ? (
                <div className="space-y-1.5">
                  <label htmlFor="vehicle_label" className={LABEL_CLASS}>
                    Véhicule externe
                  </label>
                  <input
                    id="vehicle_label"
                    name="vehicle_label"
                    maxLength={120}
                    defaultValue={transport?.vehicle.id === null ? transport.vehicle.name : ""}
                    placeholder="Transporteur externe 1234 XYZ"
                    className={FIELD_CLASS}
                  />
                </div>
              ) : null}

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
                  {pending ? "Enregistrement…" : isEdit ? "Enregistrer" : "Créer le transport"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  );
}
