"use client";

import { useState, useTransition } from "react";

import { deleteCashRegisterAction } from "@/actions/cash-registers";
import { CloseIcon, TrashIcon } from "@/components/icons";

export function DeleteCashRegisterButton({ id, label }: { id: string; label: string }) {
  const [confirming, setConfirming] = useState(false);
  const [pending, startTransition] = useTransition();

  if (!confirming) {
    return (
      <button
        type="button"
        onClick={() => setConfirming(true)}
        aria-label={`Désactiver ${label}`}
        title={`Désactiver ${label}`}
        className="rounded-lg p-1.5 text-slate-400 transition hover:bg-rose-50 hover:text-rose-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-400"
      >
        <TrashIcon className="size-4" />
      </button>
    );
  }

  return (
    <div className="flex items-center gap-1">
      <button
        type="button"
        disabled={pending}
        onClick={() =>
          startTransition(async () => {
            await deleteCashRegisterAction(id);
          })
        }
        className="rounded-lg bg-rose-600 px-2.5 py-1.5 text-xs font-semibold text-white transition hover:bg-rose-700 disabled:opacity-60"
      >
        {pending ? "Désactivation…" : "Désactiver"}
      </button>
      <button
        type="button"
        onClick={() => setConfirming(false)}
        aria-label="Annuler"
        className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
      >
        <CloseIcon className="size-4" />
      </button>
    </div>
  );
}
