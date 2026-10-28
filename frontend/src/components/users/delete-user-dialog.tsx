"use client";

import { useEffect, useState, useTransition } from "react";

import { deleteUserAction } from "@/actions/users";
import { AlertIcon, CloseIcon, TrashIcon } from "@/components/icons";
import { INITIAL_DELETE_USER_STATE, type DeleteUserState } from "@/lib/form-state";
import type { UserAccount } from "@/lib/types";
import { CANCEL_BUTTON_CLASS, FIELD_CLASS, ICON_BUTTON_CLASS, LABEL_CLASS } from "@/lib/ui";

const DANGER_BUTTON_CLASS =
  "rounded-xl bg-rose-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-rose-700 disabled:cursor-not-allowed disabled:opacity-50";

export function DeleteUserDialog({
  user,
  isSelf,
  isLastActiveAdmin,
}: {
  user: UserAccount;
  isSelf: boolean;
  isLastActiveAdmin: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [confirmation, setConfirmation] = useState("");
  const [state, setState] = useState<DeleteUserState>(INITIAL_DELETE_USER_STATE);
  const [pending, startTransition] = useTransition();

  const disabledReason = isSelf
    ? "Tu ne peux pas supprimer ton propre compte."
    : isLastActiveAdmin
      ? "Le dernier administrateur actif ne peut pas être supprimé."
      : null;
  const canDelete = confirmation === user.email;

  useEffect(() => {
    if (!open) {
      return;
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !pending) {
        setOpen(false);
        setConfirmation("");
        setState(INITIAL_DELETE_USER_STATE);
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, pending]);

  function closeDialog(): void {
    setOpen(false);
    setConfirmation("");
    setState(INITIAL_DELETE_USER_STATE);
  }

  function showDialog(): void {
    setConfirmation("");
    setState(INITIAL_DELETE_USER_STATE);
    setOpen(true);
  }

  function confirmDeletion(): void {
    if (!canDelete || pending) {
      return;
    }
    setState(INITIAL_DELETE_USER_STATE);
    startTransition(async () => {
      const next = await deleteUserAction(user.id);
      setState(next);
      if (next.status === "success") {
        closeDialog();
      }
    });
  }

  if (disabledReason) {
    return (
      <button
        type="button"
        disabled
        title={disabledReason}
        aria-label={`Supprimer définitivement ${user.email}`}
        className="inline-flex cursor-not-allowed items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-rose-600 opacity-45"
      >
        <TrashIcon className="size-4" />
        Supprimer
      </button>
    );
  }

  return (
    <>
      <button
        type="button"
        onClick={showDialog}
        aria-label={`Supprimer définitivement ${user.email}`}
        title={`Supprimer définitivement ${user.email}`}
        className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-rose-600 transition hover:bg-rose-50 hover:text-rose-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-400"
      >
        <TrashIcon className="size-4" />
        Supprimer
      </button>

      {open ? (
        <div
          role="presentation"
          onClick={() => {
            if (!pending) {
              closeDialog();
            }
          }}
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/50 p-4 backdrop-blur-sm sm:p-8"
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby={`delete-user-title-${user.id}`}
            onClick={(event) => event.stopPropagation()}
            className="animate-fade-in w-full max-w-lg rounded-2xl border border-rose-200 bg-white shadow-xl"
          >
            <header className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
              <div>
                <h2
                  id={`delete-user-title-${user.id}`}
                  className="text-lg font-semibold tracking-tight text-slate-900"
                >
                  Supprimer définitivement le compte
                </h2>
                <p className="mt-1 text-sm text-slate-500">{user.email}</p>
              </div>
              <button
                type="button"
                disabled={pending}
                onClick={closeDialog}
                aria-label="Fermer"
                className={ICON_BUTTON_CLASS}
              >
                <CloseIcon className="size-5" />
              </button>
            </header>

            <form
              onSubmit={(event) => {
                event.preventDefault();
                confirmDeletion();
              }}
              className="space-y-5 px-6 py-5"
            >
              <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
                <AlertIcon className="mt-0.5 size-5 shrink-0" />
                <div className="space-y-2">
                  <p className="font-semibold">Cette action est irréversible.</p>
                  <p>
                    Les traces métier et l&apos;historique sont conservés, mais les actions de ce
                    compte deviennent anonymes.
                  </p>
                  <p>
                    En cas de doute, désactive plutôt le compte : ses accès sont bloqués et son
                    historique reste rattaché à son identité.
                  </p>
                </div>
              </div>

              <div className="space-y-1.5">
                <label htmlFor={`delete-user-confirmation-${user.id}`} className={LABEL_CLASS}>
                  Saisis <span className="font-semibold text-slate-900">{user.email}</span> pour
                  confirmer
                </label>
                <input
                  id={`delete-user-confirmation-${user.id}`}
                  type="text"
                  value={confirmation}
                  onChange={(event) => setConfirmation(event.target.value)}
                  disabled={pending}
                  autoComplete="off"
                  autoCapitalize="none"
                  spellCheck={false}
                  autoFocus
                  className={FIELD_CLASS}
                />
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
                  disabled={pending}
                  onClick={closeDialog}
                  className={CANCEL_BUTTON_CLASS}
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  disabled={!canDelete || pending}
                  className={DANGER_BUTTON_CLASS}
                >
                  {pending ? "Suppression…" : "Supprimer définitivement"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  );
}
