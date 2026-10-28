"use client";

import { useState, useTransition } from "react";

import { resetUserPasswordAction } from "@/actions/users";
import { CloseIcon, KeyIcon } from "@/components/icons";
import { TemporaryPasswordDialog } from "@/components/users/temporary-password-dialog";
import type { PasswordResetState } from "@/lib/form-state";
import type { UserAccount } from "@/lib/types";

type Secret = {
  email: string;
  password: string;
};

export function ResetPasswordButton({ user, isSelf }: { user: UserAccount; isSelf: boolean }) {
  const [confirming, setConfirming] = useState(false);
  const [pending, startTransition] = useTransition();
  const [result, setResult] = useState<PasswordResetState>({ status: "idle" });
  const [secret, setSecret] = useState<Secret | null>(null);

  function resetPassword(): void {
    setResult({ status: "idle" });
    startTransition(async () => {
      const next = await resetUserPasswordAction(user.id);
      setResult(next);
      if (next.status === "success" && next.temporaryPassword) {
        setConfirming(false);
        setSecret({ email: user.email, password: next.temporaryPassword });
      }
    });
  }

  return (
    <>
      {confirming ? (
        <div className="flex items-center gap-1">
          <button
            type="button"
            disabled={pending}
            onClick={resetPassword}
            className="rounded-lg bg-rose-600 px-2.5 py-1.5 text-xs font-semibold text-white transition hover:bg-rose-700 disabled:opacity-60"
          >
            {pending ? "Réinitialisation…" : "Réinitialiser"}
          </button>
          <button
            type="button"
            onClick={() => setConfirming(false)}
            aria-label="Annuler la réinitialisation"
            className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
          >
            <CloseIcon className="size-4" />
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => {
            setResult({ status: "idle" });
            setConfirming(true);
          }}
          aria-label={`Réinitialiser le mot de passe de ${user.email}`}
          title="Réinitialiser le mot de passe et révoquer les sessions"
          className="rounded-lg p-1.5 text-slate-400 transition hover:bg-amber-50 hover:text-amber-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-400"
        >
          <KeyIcon className="size-4" />
        </button>
      )}

      {result.status === "error" && result.message ? (
        <p role="alert" className="mt-1 text-xs font-medium text-rose-700">
          {result.message}
        </p>
      ) : null}

      {secret ? (
        <TemporaryPasswordDialog
          email={secret.email}
          password={secret.password}
          isSelf={isSelf}
          onClose={() => setSecret(null)}
        />
      ) : null}
    </>
  );
}
