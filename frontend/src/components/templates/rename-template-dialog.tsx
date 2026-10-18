"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { AlertIcon, CloseIcon, PencilIcon } from "@/components/icons";
import {
  CANCEL_BUTTON_CLASS,
  FIELD_CLASS,
  LABEL_CLASS,
  SUBMIT_BUTTON_CLASS,
} from "@/lib/ui";

type ErrorPayload = {
  code?: string;
  detail?: string;
};

function describeError(payload: ErrorPayload | null): string {
  switch (payload?.code) {
    case "template_name_taken":
      return "Un modèle porte déjà ce nom. Choisis-en un autre.";
    case "template_name_invalid":
      return payload.detail ?? "Le nom du modèle est invalide.";
    default:
      return payload?.detail ?? "Le renommage a échoué. Réessaie dans un instant.";
  }
}

export function RenameTemplateDialog({
  templateId,
  currentName,
}: {
  templateId: string;
  currentName: string;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(currentName);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function openDialog(): void {
    setName(currentName);
    setError(null);
    setOpen(true);
  }

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      const response = await fetch(`/api/templates/${templateId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as ErrorPayload | null;
        setError(describeError(payload));
        return;
      }
      setOpen(false);
      router.refresh();
    } catch {
      setError("Impossible de joindre le serveur. Réessaie dans un instant.");
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={openDialog}
        className="inline-flex items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
      >
        <PencilIcon className="size-4" />
        Renommer
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
            aria-labelledby="rename-template-title"
            onClick={(event) => event.stopPropagation()}
            className="animate-fade-in w-full max-w-md rounded-2xl border border-slate-200 bg-white shadow-xl"
          >
            <header className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
              <div>
                <h2
                  id="rename-template-title"
                  className="text-lg font-semibold tracking-tight text-slate-900"
                >
                  Renommer le modèle
                </h2>
                <p className="mt-1 text-xs text-slate-500">
                  Le source, les variables et l&apos;historique restent inchangés.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
                aria-label="Fermer"
              >
                <CloseIcon className="size-5" />
              </button>
            </header>

            <form onSubmit={submit} className="space-y-4 px-6 py-5">
              <div>
                <label htmlFor="template-new-name" className={LABEL_CLASS}>
                  Nom du modèle
                </label>
                <input
                  id="template-new-name"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  maxLength={120}
                  required
                  autoFocus
                  className={`mt-1.5 ${FIELD_CLASS}`}
                />
              </div>

              {error ? (
                <p
                  role="alert"
                  className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-sm text-rose-700"
                >
                  <AlertIcon className="mt-0.5 size-4 shrink-0" />
                  {error}
                </p>
              ) : null}

              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className={CANCEL_BUTTON_CLASS}
                >
                  Annuler
                </button>
                <button type="submit" disabled={pending} className={SUBMIT_BUTTON_CLASS}>
                  {pending ? "Renommage…" : "Renommer"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  );
}
