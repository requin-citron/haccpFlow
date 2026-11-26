"use client";

import { useActionState, useEffect, useState } from "react";

import { closeCashSessionAction } from "@/actions/cash-sessions";
import { DenominationFields } from "@/components/cash-sessions/denomination-fields";
import { AlertIcon } from "@/components/icons";
import { useI18n } from "@/components/locale-provider";
import { isPhysicalCash } from "@/lib/cash-register";
import {
  countsDraft,
  draftTotalCents,
  eurosToCents,
  type CountsDraft,
} from "@/lib/cash-session";
import { INITIAL_CASH_SESSION_FORM_STATE } from "@/lib/form-state";
import { formatEuros } from "@/lib/format";
import { FIELD_CLASS, LABEL_CLASS, SUBMIT_BUTTON_CLASS } from "@/lib/ui";
import type { CashSession } from "@/lib/types";

export function CloseSessionForm({ session }: { session: CashSession }) {
  const { locale, t } = useI18n();
  const isCash = isPhysicalCash(session.cash_register_kind);
  const [draft, setDraft] = useState<CountsDraft>(() => countsDraft());
  const [amount, setAmount] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [state, formAction, pending] = useActionState(
    closeCashSessionAction,
    INITIAL_CASH_SESSION_FORM_STATE,
  );

  useEffect(() => {
    if (state.status === "success") {
      setConfirming(false);
      setDraft(countsDraft());
      setAmount("");
    }
  }, [state]);

  const parsedAmount = eurosToCents(amount);
  const total = isCash ? draftTotalCents(draft) : (parsedAmount ?? 0);
  const canSubmit = isCash || parsedAmount !== null;

  return (
    <form action={formAction} className="space-y-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <input type="hidden" name="session_id" value={session.id} />
      <input type="hidden" name="cash_register_kind" value={session.cash_register_kind} />

      <div>
        <h3 className="font-semibold text-slate-900">{t("Clôturer le suivi")}</h3>
        <p className="mt-0.5 text-xs text-slate-500">
          {isCash
            ? t(
                "Recompte le contenu de la caisse : ce comptage remplace l'état enregistré et le suivi devient définitif. Laisser une coupure vide revient à zéro.",
              )
            : t(
                "Saisis le montant brut encaissé pendant ce suivi. Cette valeur devient définitive à la clôture.",
              )}
        </p>
      </div>

      {isCash ? (
        <DenominationFields
          draft={draft}
          idPrefix="close_"
          onChange={(field, value) =>
            setDraft((current) => ({ ...current, [field]: value }))
          }
        />
      ) : (
        <div className="space-y-1.5">
          <label htmlFor="collected_amount" className={LABEL_CLASS}>
            {t("Montant encaissé (€)")}
          </label>
          <input
            id="collected_amount"
            name="collected_amount"
            required
            inputMode="decimal"
            value={amount}
            onChange={(event) => {
              setAmount(event.target.value);
              setConfirming(false);
            }}
            placeholder="0,00"
            className={FIELD_CLASS}
          />
          <p className="text-xs text-slate-500">
            {t("Montant brut, avant déduction des frais enregistrés.")}
          </p>
        </div>
      )}

      <p className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
        {isCash ? t("Total recompté :") : t("Encaissement du jour :")}{" "}
        <span className="text-base font-semibold tabular-nums text-slate-900">
          {formatEuros(locale, total)}
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

      <div className="flex flex-wrap items-center justify-end gap-2 border-t border-slate-100 pt-4">
        {confirming ? (
          <>
            <button
              type="button"
              onClick={() => setConfirming(false)}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
            >
              {t("Annuler")}
            </button>
            <button type="submit" disabled={pending} className={SUBMIT_BUTTON_CLASS}>
              {pending
                ? t("Clôture…")
                : t("Confirmer {amount}", { amount: formatEuros(locale, total) })}
            </button>
          </>
        ) : (
          <button
            type="button"
            onClick={() => setConfirming(true)}
            disabled={!canSubmit}
            className={SUBMIT_BUTTON_CLASS}
          >
            {t("Clôturer le suivi")}
          </button>
        )}
      </div>
    </form>
  );
}
