"use client";

import { useActionState, useEffect, useState } from "react";

import { createCashExpenseAction, updateCashExpenseAction } from "@/actions/cash-sessions";
import { AlertIcon, CloseIcon, PencilIcon, PlusIcon } from "@/components/icons";
import {
  EXPENSE_KIND_HINTS,
  EXPENSE_KIND_LABELS,
  centsToEurosInput,
  eurosToCents,
} from "@/lib/cash-session";
import { INITIAL_CASH_SESSION_FORM_STATE } from "@/lib/form-state";
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
import type { CashExpense, CashExpenseKind } from "@/lib/types";

function defaultVatRate(kind: CashExpenseKind): string {
  return kind === "professional" ? "20" : "0";
}

export function ExpenseFormDialog({
  sessionId,
  expense,
}: {
  sessionId: string;
  expense?: CashExpense;
}) {
  const isEdit = expense !== undefined;
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<CashExpenseKind>(expense?.kind ?? "professional");
  const [quantity, setQuantity] = useState(String(expense?.quantity ?? 1));
  const [unitPrice, setUnitPrice] = useState(
    expense ? centsToEurosInput(expense.unit_price_cents) : "",
  );
  const [vatRate, setVatRate] = useState(
    expense?.vat_rate ?? defaultVatRate(expense?.kind ?? "professional"),
  );
  const [state, formAction, pending] = useActionState(
    isEdit ? updateCashExpenseAction : createCashExpenseAction,
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

  const quantityValue = Math.floor(Number(quantity));
  const lineTotalCents =
    (Number.isFinite(quantityValue) && quantityValue > 0 ? quantityValue : 0) *
    (eurosToCents(unitPrice) ?? 0);

  const startEditing = () => {
    setKind(expense?.kind ?? "professional");
    setQuantity(String(expense?.quantity ?? 1));
    setUnitPrice(expense ? centsToEurosInput(expense.unit_price_cents) : "");
    setVatRate(expense?.vat_rate ?? defaultVatRate(expense?.kind ?? "professional"));
    setOpen(true);
  };

  return (
    <>
      {isEdit ? (
        <button
          type="button"
          onClick={startEditing}
          aria-label={`Modifier ${expense.name}`}
          title={`Modifier ${expense.name}`}
          className={SECONDARY_TRIGGER_CLASS}
        >
          <PencilIcon className="size-4" />
        </button>
      ) : (
        <button type="button" onClick={startEditing} className={PRIMARY_TRIGGER_CLASS}>
          <PlusIcon className="size-4" />
          Ajouter un frais
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
            aria-labelledby="expense-form-title"
            onClick={(event) => event.stopPropagation()}
            className="animate-fade-in w-full max-w-md rounded-2xl border border-slate-200 bg-white shadow-xl"
          >
            <header className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
              <div>
                <h2
                  id="expense-form-title"
                  className="text-lg font-semibold tracking-tight text-slate-900"
                >
                  {isEdit ? "Modifier le frais" : "Nouveau frais"}
                </h2>
                <p className="mt-0.5 text-sm text-slate-500">
                  Argent sorti de la caisse pendant le suivi.
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
              <input type="hidden" name="session_id" value={sessionId} />
              {isEdit ? <input type="hidden" name="expense_id" value={expense.id} /> : null}

              <div className="space-y-2">
                <span className={LABEL_CLASS}>Type de frais</span>
                <div className="grid grid-cols-2 gap-2">
                  {(["professional", "personal"] as const).map((option) => (
                    <label
                      key={option}
                      className={`flex cursor-pointer items-start gap-2 rounded-xl border px-3.5 py-2.5 text-sm transition ${
                        kind === option
                          ? "border-teal-500 bg-teal-50/60 text-teal-900"
                          : "border-slate-200 text-slate-600 hover:border-slate-300"
                      }`}
                    >
                      <input
                        type="radio"
                        name="kind"
                        value={option}
                        checked={kind === option}
                        onChange={() => {
                          setKind(option);
                          setVatRate(defaultVatRate(option));
                        }}
                        className="mt-0.5 size-4 border-slate-300 text-teal-600 focus:ring-teal-500/30"
                      />
                      <span>
                        <span className="block font-medium">{EXPENSE_KIND_LABELS[option]}</span>
                        <span className="mt-0.5 block text-[11px] leading-snug text-slate-500">
                          {EXPENSE_KIND_HINTS[option]}
                        </span>
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <label htmlFor="expense_name" className={LABEL_CLASS}>
                  Nom du frais
                </label>
                <input
                  id="expense_name"
                  name="name"
                  required
                  maxLength={160}
                  autoFocus
                  defaultValue={expense?.name ?? ""}
                  placeholder="Sacs poubelle"
                  className={FIELD_CLASS}
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                <div className="space-y-1.5">
                  <label htmlFor="expense_quantity" className={LABEL_CLASS}>
                    Quantité
                  </label>
                  <input
                    id="expense_quantity"
                    name="quantity"
                    type="number"
                    min={1}
                    step={1}
                    inputMode="numeric"
                    required
                    value={quantity}
                    onChange={(event) => setQuantity(event.target.value)}
                    className={FIELD_CLASS}
                  />
                </div>
                <div className="space-y-1.5">
                  <label htmlFor="expense_unit_price" className={LABEL_CLASS}>
                    Prix unitaire (€)
                  </label>
                  <input
                    id="expense_unit_price"
                    name="unit_price"
                    type="number"
                    min={0}
                    step="0.01"
                    inputMode="decimal"
                    required
                    value={unitPrice}
                    onChange={(event) => setUnitPrice(event.target.value)}
                    placeholder="12.50"
                    className={FIELD_CLASS}
                  />
                </div>
                <div className="space-y-1.5">
                  <label htmlFor="expense_vat_rate" className={LABEL_CLASS}>
                    TVA (%)
                  </label>
                  <input
                    id="expense_vat_rate"
                    name="vat_rate"
                    type="number"
                    min={0}
                    max={100}
                    step="0.1"
                    inputMode="decimal"
                    value={vatRate}
                    onChange={(event) => setVatRate(event.target.value)}
                    className={FIELD_CLASS}
                  />
                </div>
              </div>

              <p className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
                Total du frais :{" "}
                <span className="text-base font-semibold tabular-nums text-slate-900">
                  {formatEuros(lineTotalCents)}
                </span>
                <span className="mt-0.5 block text-xs text-slate-500">
                  Prix unitaire TTC : la TVA est conservée pour l&apos;archivage.
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
                  {pending ? "Enregistrement…" : isEdit ? "Enregistrer" : "Ajouter le frais"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  );
}
