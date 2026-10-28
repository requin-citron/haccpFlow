"use client";

import { useEffect, useRef, useState } from "react";

import { AlertIcon, CheckIcon, CloseIcon, CopyIcon, LogOutIcon } from "@/components/icons";
import { CANCEL_BUTTON_CLASS, ICON_BUTTON_CLASS, SUBMIT_BUTTON_CLASS } from "@/lib/ui";

export function TemporaryPasswordDialog({
  email,
  password,
  isSelf,
  onClose,
}: {
  email: string;
  password: string;
  isSelf: boolean;
  onClose: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState<string | null>(null);

  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  async function copyPassword(): Promise<void> {
    setCopyError(null);
    try {
      await navigator.clipboard.writeText(password);
      setCopied(true);
    } catch {
      setCopyError("La copie automatique a échoué. Sélectionne le mot de passe manuellement.");
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }

  function close(): void {
    if (isSelf) {
      window.location.assign("/login");
      return;
    }
    onClose();
  }

  return (
    <div
      role="presentation"
      className="fixed inset-0 z-[60] flex items-start justify-center overflow-y-auto bg-slate-900/60 p-4 backdrop-blur-sm sm:p-8"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="temporary-password-title"
        className="animate-fade-in w-full max-w-lg rounded-2xl border border-slate-200 bg-white shadow-xl"
      >
        <header className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
          <div>
            <h2
              id="temporary-password-title"
              className="text-lg font-semibold tracking-tight text-slate-900"
            >
              Mot de passe généré
            </h2>
            <p className="mt-0.5 text-sm text-slate-500">{email}</p>
          </div>
          <button type="button" onClick={close} aria-label="Fermer" className={ICON_BUTTON_CLASS}>
            <CloseIcon className="size-5" />
          </button>
        </header>

        <div className="space-y-4 px-6 py-5">
          <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3.5 py-3 text-sm text-amber-800">
            <AlertIcon className="mt-0.5 size-4 shrink-0" />
            <p>
              Ce mot de passe ne sera plus affiché. Copie-le maintenant dans ton gestionnaire de
              secrets.
            </p>
          </div>

          <div>
            <label htmlFor="temporary-password-value" className="block text-sm font-medium text-slate-700">
              Mot de passe
            </label>
            <div className="mt-1.5 flex gap-2">
              <input
                ref={inputRef}
                id="temporary-password-value"
                value={password}
                readOnly
                spellCheck={false}
                onFocus={(event) => event.currentTarget.select()}
                className="min-w-0 flex-1 rounded-xl border border-slate-300 bg-slate-50 px-3.5 py-2.5 font-mono text-sm text-slate-900 outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-500/15"
              />
              <button type="button" onClick={copyPassword} className={CANCEL_BUTTON_CLASS}>
                {copied ? <CheckIcon className="size-4 text-emerald-600" /> : <CopyIcon className="size-4" />}
                {copied ? "Copié" : "Copier"}
              </button>
            </div>
            {copyError ? (
              <p role="alert" className="mt-2 text-xs font-medium text-rose-700">
                {copyError}
              </p>
            ) : null}
          </div>

          {isSelf ? (
            <p className="rounded-xl bg-slate-50 px-3.5 py-3 text-sm text-slate-600">
              Ce changement a révoqué ta session courante. Tu devras te reconnecter avec ce nouveau
              mot de passe.
            </p>
          ) : null}

          <div className="flex justify-end border-t border-slate-100 pt-4">
            <button type="button" onClick={close} className={SUBMIT_BUTTON_CLASS}>
              {isSelf ? <LogOutIcon className="size-4" /> : null}
              {isSelf ? "Se reconnecter" : "J'ai enregistré le mot de passe"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
