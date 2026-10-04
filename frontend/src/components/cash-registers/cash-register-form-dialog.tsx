"use client";

import { useActionState, useEffect, useState } from "react";

import {
  createCashRegisterAction,
  updateCashRegisterAction,
} from "@/actions/cash-registers";
import { AlertIcon, CloseIcon, PencilIcon, PlusIcon } from "@/components/icons";
import {
  COIN_DENOMINATIONS,
  DENOMINATIONS,
  NOTE_DENOMINATIONS,
  countsOf,
  emptyCounts,
  type Denomination,
} from "@/lib/cash-register";
import { INITIAL_CASH_REGISTER_FORM_STATE } from "@/lib/form-state";
import { formatEuros } from "@/lib/format";
import {
  CANCEL_BUTTON_CLASS,
  FIELD_CLASS,
  ICON_BUTTON_CLASS,
  LABEL_CLASS,
  PRIMARY_TRIGGER_CLASS,
  SECONDARY_TRIGGER_CLASS,
  SUBMIT_BUTTON_CLASS,
} from "@/lib/ui";
import type { CashRegister } from "@/lib/types";

type Draft = Record<string, string>;

/** The form shows only what is counted: a zero stays an empty field. */
function toDraft(cashRegister?: CashRegister): Draft {
  const counts = cashRegister ? countsOf(cashRegister) : emptyCounts();
  return Object.fromEntries(
    DENOMINATIONS.map((denomination) => {
      const count = counts[denomination.field];
      return [denomination.field, count > 0 ? String(count) : ""];
    }),
  );
}

function draftTotal(draft: Draft): number {
  return DENOMINATIONS.reduce((total, denomination) => {
    const value = Number(draft[denomination.field] ?? "");
    const count = Number.isFinite(value) && value > 0 ? Math.floor(value) : 0;
    return total + count * denomination.cents;
  }, 0);
}

function CountField({
  denomination,
  value,
  onChange,
}: {
  denomination: Denomination;
  value: string;
  onChange: (field: string, value: string) => void;
}) {
  return (
    <div className="space-y-1">
      <label htmlFor={denomination.field} className="block text-[11px] font-medium text-slate-600">
        {denomination.label}
      </label>
      <input
        id={denomination.field}
        name={denomination.field}
        type="number"
        min={0}
        step={1}
        inputMode="numeric"
        value={value}
        placeholder="0"
        onChange={(event) => onChange(denomination.field, event.target.value)}
        className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-sm tabular-nums text-slate-900 shadow-sm outline-none transition placeholder:text-slate-300 focus:border-teal-500 focus:ring-4 focus:ring-teal-500/15"
      />
    </div>
  );
}

export function CashRegisterFormDialog({ cashRegister }: { cashRegister?: CashRegister }) {
  const isEdit = cashRegister !== undefined;
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<Draft>(() => toDraft(cashRegister));
  const [state, formAction, pending] = useActionState(
    isEdit ? updateCashRegisterAction : createCashRegisterAction,
    INITIAL_CASH_REGISTER_FORM_STATE,
  );

  useEffect(() => {
    if (state.status === "success") {
      setOpen(false);
      setDraft(toDraft());
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

  const updateField = (field: string, value: string) => {
    setDraft((current) => ({ ...current, [field]: value }));
  };

  return (
    <>
      {isEdit ? (
        <button
          type="button"
          onClick={() => {
            setDraft(toDraft(cashRegister));
            setOpen(true);
          }}
          aria-label={`Modifier ${cashRegister.name}`}
          className={SECONDARY_TRIGGER_CLASS}
        >
          <PencilIcon className="size-4" />
          Modifier
        </button>
      ) : (
        <button
          type="button"
          onClick={() => {
            setDraft(toDraft());
            setOpen(true);
          }}
          className={PRIMARY_TRIGGER_CLASS}
        >
          <PlusIcon className="size-4" />
          Nouvelle caisse
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
            aria-labelledby="cash-register-form-title"
            onClick={(event) => event.stopPropagation()}
            className="animate-fade-in w-full max-w-lg rounded-2xl border border-slate-200 bg-white shadow-xl"
          >
            <header className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
              <div>
                <h2
                  id="cash-register-form-title"
                  className="text-lg font-semibold tracking-tight text-slate-900"
                >
                  {isEdit ? "Modifier la caisse" : "Nouvelle caisse"}
                </h2>
                <p className="mt-0.5 text-sm text-slate-500">
                  Saisis le comptage initial, coupure par coupure.
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
              {isEdit ? <input type="hidden" name="id" value={cashRegister.id} /> : null}

              <div className="space-y-1.5">
                <label htmlFor="name" className={LABEL_CLASS}>
                  Nom de la caisse
                </label>
                <input
                  id="name"
                  name="name"
                  required
                  maxLength={120}
                  autoFocus
                  defaultValue={cashRegister?.name ?? ""}
                  placeholder="Caisse principale"
                  className={FIELD_CLASS}
                />
              </div>

              <fieldset className="space-y-2">
                <legend className={LABEL_CLASS}>Pièces</legend>
                <div className="grid grid-cols-4 gap-3">
                  {COIN_DENOMINATIONS.map((denomination) => (
                    <CountField
                      key={denomination.field}
                      denomination={denomination}
                      value={draft[denomination.field] ?? ""}
                      onChange={updateField}
                    />
                  ))}
                </div>
              </fieldset>

              <fieldset className="space-y-2">
                <legend className={LABEL_CLASS}>Billets</legend>
                <div className="grid grid-cols-4 gap-3">
                  {NOTE_DENOMINATIONS.map((denomination) => (
                    <CountField
                      key={denomination.field}
                      denomination={denomination}
                      value={draft[denomination.field] ?? ""}
                      onChange={updateField}
                    />
                  ))}
                </div>
              </fieldset>

              <p className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
                Total du comptage :{" "}
                <span className="text-base font-semibold tabular-nums text-slate-900">
                  {formatEuros(draftTotal(draft))}
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
                  {pending ? "Enregistrement…" : isEdit ? "Enregistrer" : "Créer la caisse"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  );
}
