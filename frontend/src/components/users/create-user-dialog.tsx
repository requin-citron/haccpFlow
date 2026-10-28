"use client";

import { useActionState, useEffect, useRef, useState } from "react";

import { createUserAction } from "@/actions/users";
import { AlertIcon, CloseIcon, PlusIcon } from "@/components/icons";
import { TemporaryPasswordDialog } from "@/components/users/temporary-password-dialog";
import { INITIAL_USER_FORM_STATE } from "@/lib/form-state";
import {
  CANCEL_BUTTON_CLASS,
  FIELD_CLASS,
  ICON_BUTTON_CLASS,
  LABEL_CLASS,
  PRIMARY_TRIGGER_CLASS,
  SUBMIT_BUTTON_CLASS,
} from "@/lib/ui";
import { USER_ROLE_LABELS } from "@/lib/users";

type Secret = {
  email: string;
  password: string;
};

export function CreateUserDialog() {
  const [open, setOpen] = useState(false);
  const [secret, setSecret] = useState<Secret | null>(null);
  const [state, formAction, pending] = useActionState(
    createUserAction,
    INITIAL_USER_FORM_STATE,
  );
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    if (state.status === "success" && state.user && state.temporaryPassword) {
      formRef.current?.reset();
      setOpen(false);
      setSecret({
        email: state.user.email,
        password: state.temporaryPassword,
      });
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
      <button type="button" onClick={() => setOpen(true)} className={PRIMARY_TRIGGER_CLASS}>
        <PlusIcon className="size-4" />
        Nouvel utilisateur
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
            aria-labelledby="create-user-title"
            onClick={(event) => event.stopPropagation()}
            className="animate-fade-in w-full max-w-md rounded-2xl border border-slate-200 bg-white shadow-xl"
          >
            <header className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
              <div>
                <h2
                  id="create-user-title"
                  className="text-lg font-semibold tracking-tight text-slate-900"
                >
                  Nouvel utilisateur
                </h2>
                <p className="mt-0.5 text-sm text-slate-500">
                  Un mot de passe fort sera généré et affiché une seule fois.
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

            <form ref={formRef} action={formAction} className="space-y-5 px-6 py-5">
              <div className="space-y-1.5">
                <label htmlFor="user-email" className={LABEL_CLASS}>
                  Email
                </label>
                <input
                  id="user-email"
                  name="email"
                  type="email"
                  required
                  autoFocus
                  maxLength={320}
                  placeholder="operateur@exemple.fr"
                  className={FIELD_CLASS}
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="user-role" className={LABEL_CLASS}>
                  Rôle
                </label>
                <select id="user-role" name="role" defaultValue="operator" className={FIELD_CLASS}>
                  {Object.entries(USER_ROLE_LABELS).map(([role, label]) => (
                    <option key={role} value={role}>
                      {label}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-slate-500">
                  Les administrateurs peuvent gérer les comptes et les référentiels.
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
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className={CANCEL_BUTTON_CLASS}
                >
                  Annuler
                </button>
                <button type="submit" disabled={pending} className={SUBMIT_BUTTON_CLASS}>
                  {pending ? "Création…" : "Créer le compte"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {secret ? (
        <TemporaryPasswordDialog
          email={secret.email}
          password={secret.password}
          isSelf={false}
          onClose={() => setSecret(null)}
        />
      ) : null}
    </>
  );
}
