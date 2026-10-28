"use client";

import { useActionState, useEffect, useState } from "react";

import { updateUserAction } from "@/actions/users";
import { AlertIcon, CloseIcon, PencilIcon } from "@/components/icons";
import { INITIAL_USER_FORM_STATE } from "@/lib/form-state";
import {
  CANCEL_BUTTON_CLASS,
  FIELD_CLASS,
  ICON_BUTTON_CLASS,
  LABEL_CLASS,
  SECONDARY_TRIGGER_CLASS,
  SUBMIT_BUTTON_CLASS,
} from "@/lib/ui";
import type { UserAccount } from "@/lib/types";
import { USER_ROLE_LABELS } from "@/lib/users";

export function EditUserDialog({ user, isSelf }: { user: UserAccount; isSelf: boolean }) {
  const [open, setOpen] = useState(false);
  const [state, formAction, pending] = useActionState(
    updateUserAction,
    INITIAL_USER_FORM_STATE,
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

  if (isSelf) {
    return (
      <button
        type="button"
        disabled
        title="Tu ne peux pas modifier tes propres droits."
        className={`${SECONDARY_TRIGGER_CLASS} cursor-not-allowed opacity-45`}
      >
        <PencilIcon className="size-4" />
        Modifier
      </button>
    );
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={`Modifier ${user.email}`}
        className={SECONDARY_TRIGGER_CLASS}
      >
        <PencilIcon className="size-4" />
        Modifier
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
            aria-labelledby="edit-user-title"
            onClick={(event) => event.stopPropagation()}
            className="animate-fade-in w-full max-w-md rounded-2xl border border-slate-200 bg-white shadow-xl"
          >
            <header className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
              <div>
                <h2
                  id="edit-user-title"
                  className="text-lg font-semibold tracking-tight text-slate-900"
                >
                  Modifier l&apos;utilisateur
                </h2>
                <p className="mt-0.5 text-sm text-slate-500">{user.email}</p>
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
              <input type="hidden" name="id" value={user.id} />

              <div className="space-y-1.5">
                <label htmlFor={`user-email-${user.id}`} className={LABEL_CLASS}>
                  Email
                </label>
                <input
                  id={`user-email-${user.id}`}
                  value={user.email}
                  readOnly
                  className={`${FIELD_CLASS} bg-slate-50 text-slate-500`}
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor={`user-role-${user.id}`} className={LABEL_CLASS}>
                  Rôle
                </label>
                <select
                  id={`user-role-${user.id}`}
                  name="role"
                  defaultValue={user.role}
                  className={FIELD_CLASS}
                >
                  {Object.entries(USER_ROLE_LABELS).map(([role, label]) => (
                    <option key={role} value={role}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <label htmlFor={`user-active-${user.id}`} className={LABEL_CLASS}>
                  État du compte
                </label>
                <select
                  id={`user-active-${user.id}`}
                  name="is_active"
                  defaultValue={user.is_active ? "true" : "false"}
                  className={FIELD_CLASS}
                >
                  <option value="true">Actif</option>
                  <option value="false">Inactif — connexions bloquées</option>
                </select>
                <p className="text-xs text-slate-500">
                  La désactivation révoque immédiatement les sessions du compte.
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
                  {pending ? "Enregistrement…" : "Enregistrer"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  );
}
