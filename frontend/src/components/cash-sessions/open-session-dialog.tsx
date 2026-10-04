"use client";

import { useActionState, useEffect, useState } from "react";

import { openCashSessionAction } from "@/actions/cash-sessions";
import { DenominationFields } from "@/components/cash-sessions/denomination-fields";
import { AlertIcon, CloseIcon, PlusIcon } from "@/components/icons";
import { countsDraft, draftTotalCents, type CountsDraft } from "@/lib/cash-session";
import { INITIAL_CASH_SESSION_FORM_STATE } from "@/lib/form-state";
import { formatEuros, todayIso } from "@/lib/format";
import {
  CANCEL_BUTTON_CLASS,
  FIELD_CLASS,
  ICON_BUTTON_CLASS,
  LABEL_CLASS,
  PRIMARY_TRIGGER_CLASS,
  SUBMIT_BUTTON_CLASS,
} from "@/lib/ui";
import type { CashRegister } from "@/lib/types";

export function OpenSessionDialog({ cashRegisters }: { cashRegisters: CashRegister[] }) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<CountsDraft>(() => countsDraft());
  const [registerId, setRegisterId] = useState(cashRegisters[0]?.id ?? "");
  const [override, setOverride] = useState(false);
  const [state, formAction, pending] = useActionState(
    openCashSessionAction,
    INITIAL_CASH_SESSION_FORM_STATE,
  );

  useEffect(() => {
    if (state.status === "success") {
      setOpen(false);
      setOverride(false);
      setDraft(countsDraft());
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

  const selected = cashRegisters.find((cashRegister) => cashRegister.id === registerId);

  return (
    <>
      <button
        type="button"
        onClick={() => {
          setDraft(countsDraft());
          setOverride(false);
          setOpen(true);
        }}
        disabled={cashRegisters.length === 0}
        className={`${PRIMARY_TRIGGER_CLASS} disabled:cursor-not-allowed disabled:opacity-50`}
      >
        <PlusIcon className="size-4" />
        Ouvrir un suivi
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
            aria-labelledby="open-session-title"
            onClick={(event) => event.stopPropagation()}
            className="animate-fade-in w-full max-w-lg rounded-2xl border border-slate-200 bg-white shadow-xl"
          >
            <header className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
              <div>
                <h2
                  id="open-session-title"
                  className="text-lg font-semibold tracking-tight text-slate-900"
                >
                  Ouvrir un suivi de caisse
                </h2>
                <p className="mt-0.5 text-sm text-slate-500">
                  Le fond de caisse est repris de la caisse, puis les frais s&apos;ajoutent au fil
                  de la journée.
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
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label htmlFor="cash_register_id" className={LABEL_CLASS}>
                    Caisse
                  </label>
                  <select
                    id="cash_register_id"
                    name="cash_register_id"
                    value={registerId}
                    onChange={(event) => setRegisterId(event.target.value)}
                    className={FIELD_CLASS}
                  >
                    {cashRegisters.map((cashRegister) => (
                      <option key={cashRegister.id} value={cashRegister.id}>
                        {cashRegister.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1.5">
                  <label htmlFor="session_date" className={LABEL_CLASS}>
                    Date du suivi
                  </label>
                  <input
                    id="session_date"
                    name="session_date"
                    type="date"
                    required
                    defaultValue={todayIso()}
                    className={FIELD_CLASS}
                  />
                </div>
              </div>

              {override ? (
                <>
                  <DenominationFields
                    draft={draft}
                    idPrefix="open_"
                    onChange={(field, value) => setDraft((current) => ({ ...current, [field]: value }))}
                  />
                  <p className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
                    Fond saisi :{" "}
                    <span className="text-base font-semibold tabular-nums text-slate-900">
                      {formatEuros(draftTotalCents(draft))}
                    </span>
                  </p>
                </>
              ) : (
                <p className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
                  Fond repris de la caisse :{" "}
                  <span className="text-base font-semibold tabular-nums text-slate-900">
                    {formatEuros(selected?.total_cents ?? 0)}
                  </span>
                </p>
              )}

              <label className="flex items-start gap-2.5 rounded-xl border border-slate-200 px-3.5 py-3 text-sm text-slate-700">
                <input
                  type="checkbox"
                  name="override_opening"
                  value="1"
                  checked={override}
                  onChange={(event) => {
                    setOverride(event.target.checked);
                    if (!event.target.checked) {
                      setDraft(countsDraft());
                    }
                  }}
                  className="mt-0.5 size-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500/30"
                />
                <span>
                  Forcer le fond de caisse
                  <span className="mt-0.5 block text-xs text-slate-500">
                    À cocher si le comptage enregistré ne correspond pas au contenu réel.
                  </span>
                </span>
              </label>

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
                  {pending ? "Ouverture…" : "Ouvrir le suivi"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  );
}
