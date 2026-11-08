"use client";

import { useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { AlertIcon, CheckIcon, FileTextIcon } from "@/components/icons";
import { useI18n } from "@/components/locale-provider";
import { t, type Locale } from "@/lib/i18n";
import { FIELD_CLASS, LABEL_CLASS, SUBMIT_BUTTON_CLASS } from "@/lib/ui";

type ApiPayload = {
  code?: string;
  detail?: string;
  name?: string;
};

function describeError(payload: ApiPayload | null, locale: Locale): string {
  switch (payload?.code) {
    case "template_name_taken":
      return t(locale, "Un modèle porte déjà ce nom. Choisis-en un autre.");
    case "template_too_large":
      return t(locale, "Le fichier dépasse la taille maximale autorisée.");
    case "template_type_not_allowed":
      return t(locale, "Seuls les fichiers .tex sont acceptés.");
    case "template_empty":
      return t(locale, "Le fichier est vide.");
    case "template_invalid_encoding":
    case "template_invalid_content":
      return t(locale, "Le fichier doit être un texte LaTeX UTF-8 valide, sans caractères binaires.");
    case "template_name_invalid":
      return t(locale, "Le nom du modèle est invalide (120 caractères maximum).");
    default:
      return payload?.detail ?? t(locale, "L'import a échoué. Réessaie dans un instant.");
  }
}

export function UploadTemplateForm() {
  const { locale, t } = useI18n();
  const router = useRouter();
  const formRef = useRef<HTMLFormElement>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const file = formData.get("file");

    if (!(file instanceof File) || file.size === 0) {
      setError(t("Choisis un fichier .tex à importer."));
      setSuccess(null);
      return;
    }
    if (!file.name.toLowerCase().endsWith(".tex")) {
      setError(t("Seuls les fichiers .tex sont acceptés."));
      setSuccess(null);
      return;
    }

    setPending(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await fetch("/api/templates", { method: "POST", body: formData });
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      const payload = (await response.json().catch(() => null)) as ApiPayload | null;
      if (!response.ok) {
        setError(describeError(payload, locale));
        return;
      }
      form.reset();
      setSuccess(
        t("« {name} » a été importé.", {
          name: payload?.name ?? t("Modèle"),
        }),
      );
      router.refresh();
    } catch {
      setError(t("Impossible de joindre le serveur. Réessaie dans un instant."));
    } finally {
      setPending(false);
    }
  }

  return (
    <form
      ref={formRef}
      onSubmit={handleSubmit}
      className="rounded-2xl border border-slate-200 bg-white px-5 py-5 shadow-sm"
    >
      <div className="flex items-start gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-teal-50 text-teal-700">
          <FileTextIcon className="size-5" />
        </span>
        <div>
          <h2 className="text-sm font-semibold text-slate-900">{t("Importer un modèle")}</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            {t("Le fichier source est conservé tel quel, sans compilation.")}
          </p>
        </div>
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="template-file" className={LABEL_CLASS}>
            {t("Fichier LaTeX")}
          </label>
          <input
            id="template-file"
            name="file"
            type="file"
            accept=".tex"
            required
            className="mt-1.5 block w-full cursor-pointer rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-700 shadow-sm outline-none transition file:mr-3 file:rounded-lg file:border-0 file:bg-teal-50 file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-teal-700 hover:file:bg-teal-100 focus:border-teal-500 focus:ring-4 focus:ring-teal-500/15"
          />
          <p className="mt-1 text-xs text-slate-500">{t("Extension .tex, encodage UTF-8.")}</p>
        </div>
        <div>
          <label htmlFor="template-name" className={LABEL_CLASS}>
            {t("Nom {optional}", { optional: t("(facultatif)") })}
          </label>
          <input
            id="template-name"
            name="name"
            type="text"
            maxLength={120}
            placeholder={t("Bon de livraison")}
            className={`mt-1.5 ${FIELD_CLASS}`}
          />
          <p className="mt-1 text-xs text-slate-500">
            {t("À défaut, le nom du fichier sans extension est utilisé.")}
          </p>
        </div>
      </div>

      {error ? (
        <p
          role="alert"
          className="mt-4 flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-sm text-rose-700"
        >
          <AlertIcon className="mt-0.5 size-4 shrink-0" />
          {error}
        </p>
      ) : null}

      {success ? (
        <p
          role="status"
          className="mt-4 flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3.5 py-2.5 text-sm text-emerald-700"
        >
          <CheckIcon className="mt-0.5 size-4 shrink-0" />
          {success}
        </p>
      ) : null}

      <div className="mt-5 flex justify-end">
        <button type="submit" disabled={pending} className={SUBMIT_BUTTON_CLASS}>
          {pending ? t("Import en cours…") : t("Importer le modèle")}
        </button>
      </div>
    </form>
  );
}
