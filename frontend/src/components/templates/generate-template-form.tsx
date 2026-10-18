"use client";

import { useMemo, useState, type FormEvent } from "react";

import {
  AlertIcon,
  CheckIcon,
  CloseIcon,
  DownloadIcon,
  FileTextIcon,
} from "@/components/icons";
import {
  ProductRowsEditor,
  productRowsFromValue,
  productRowsToPayload,
  validateProductRows,
  type ProductRowDraft,
} from "@/components/templates/product-rows-editor";
import { FIELD_CLASS, LABEL_CLASS, SUBMIT_BUTTON_CLASS } from "@/lib/ui";
import type { GeneratedDocument, ProductRow, TemplateVariable } from "@/lib/types";

type ErrorPayload = {
  code?: string;
  detail?: string;
  context?: Record<string, unknown> | null;
};

type ErrorDetails = {
  message: string;
  log?: string;
};

function describeError(payload: ErrorPayload | null): ErrorDetails {
  const missing = Array.isArray(payload?.context?.missing)
    ? payload.context.missing.map(String)
    : [];
  switch (payload?.code) {
    case "template_values_missing":
      return {
        message: `Renseigne les valeurs obligatoires : ${missing.join(", ") || "champs manquants"}.`,
      };
    case "template_values_unknown":
      return { message: "Une valeur ne correspond à aucune variable du modèle." };
    case "template_values_static":
      return { message: "Une variable statique a été fournie par erreur." };
    case "template_value_invalid":
      return { message: payload.detail ?? "Une valeur est invalide." };
    case "template_render_failed":
      return {
        message: payload.detail ?? "Le modèle n'a pas pu être rendu avec ces valeurs.",
      };
    case "template_compilation_failed":
      return {
        message: "La compilation LaTeX du document a échoué.",
        log: typeof payload.context?.log === "string" ? payload.context.log : undefined,
      };
    case "template_compilation_timeout":
      return { message: "La compilation LaTeX a dépassé le délai autorisé." };
    default:
      return { message: payload?.detail ?? "La génération a échoué. Réessaie dans un instant." };
  }
}

type FormValues = Record<string, string | ProductRowDraft[]>;

function initialValues(variables: TemplateVariable[]): FormValues {
  const initial: FormValues = {};
  for (const variable of variables) {
    if (variable.kind !== "local") {
      continue;
    }
    initial[variable.name] =
      variable.value_type === "products"
        ? productRowsFromValue(variable.value)
        : typeof variable.value === "string"
          ? variable.value
          : "";
  }
  return initial;
}

function scalarValue(values: FormValues, name: string): string {
  const value = values[name];
  return typeof value === "string" ? value : "";
}

function productDraftRows(values: FormValues, name: string): ProductRowDraft[] {
  const value = values[name];
  return Array.isArray(value) ? value : [];
}

function buildValues(
  variables: TemplateVariable[],
  values: FormValues,
): { values: Record<string, string | ProductRow[]>; error?: string } {
  const payload: Record<string, string | ProductRow[]> = {};
  for (const variable of variables) {
    if (variable.kind !== "local") {
      continue;
    }
    if (variable.value_type === "products") {
      const drafts = productDraftRows(values, variable.name);
      const rowsError = validateProductRows(drafts);
      if (rowsError) {
        return { values: {}, error: `${variable.label} : ${rowsError}` };
      }
      payload[variable.name] = productRowsToPayload(drafts);
      continue;
    }
    const value = scalarValue(values, variable.name);
    if (value) {
      payload[variable.name] = value;
    }
  }
  return { values: payload };
}

export function GenerateTemplateForm({
  templateId,
  templateName,
  variables,
  isAdmin,
}: {
  templateId: string;
  templateName: string;
  variables: TemplateVariable[];
  isAdmin: boolean;
}) {
  const localVariables = useMemo(
    () => variables.filter((variable) => variable.kind === "local"),
    [variables],
  );
  const localScalars = useMemo(
    () => localVariables.filter((variable) => variable.value_type !== "products"),
    [localVariables],
  );
  const localProducts = useMemo(
    () => localVariables.filter((variable) => variable.value_type === "products"),
    [localVariables],
  );
  const [values, setValues] = useState<FormValues>(() => initialValues(variables));
  const [pending, setPending] = useState(false);
  const [previewPending, setPreviewPending] = useState(false);
  const [error, setError] = useState<ErrorDetails | null>(null);
  const [generatedDocument, setGeneratedDocument] = useState<GeneratedDocument | null>(null);
  const [preview, setPreview] = useState<string | null>(null);

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setGeneratedDocument(null);
    const built = buildValues(localVariables, values);
    if (built.error) {
      setError({ message: built.error });
      return;
    }
    setPending(true);
    try {
      const response = await fetch(`/api/templates/${templateId}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ values: built.values }),
      });
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      const payload = (await response.json().catch(() => null)) as
        | (GeneratedDocument & ErrorPayload)
        | null;
      if (!response.ok) {
        setError(describeError(payload));
        return;
      }
      if (payload) {
        setGeneratedDocument(payload);
        const link = document.createElement("a");
        link.href = `/api/documents/${payload.id}/download`;
        document.body.appendChild(link);
        link.click();
        link.remove();
      }
    } catch {
      setError({ message: "Impossible de joindre le serveur. Réessaie dans un instant." });
    } finally {
      setPending(false);
    }
  }

  async function openPreview() {
    setError(null);
    const built = buildValues(localVariables, values);
    if (built.error) {
      setError({ message: built.error });
      return;
    }
    setPreviewPending(true);
    try {
      const response = await fetch(`/api/templates/${templateId}/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ values: built.values }),
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
      setPreview(await response.text());
    } catch {
      setError({ message: "Impossible de joindre le serveur. Réessaie dans un instant." });
    } finally {
      setPreviewPending(false);
    }
  }

  return (
    <>
      <form
        onSubmit={generate}
        className="rounded-2xl border border-slate-200 bg-white px-5 py-5 shadow-sm"
      >
        <div className="flex items-start gap-3">
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-teal-50 text-teal-700">
            <FileTextIcon className="size-5" />
          </span>
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Générer le document</h2>
            <p className="mt-0.5 text-xs text-slate-500">
              Renseigne les valeurs locales ; les variables statiques sont intégrées
              automatiquement.
            </p>
          </div>
        </div>

        {localVariables.length === 0 ? (
          <p className="mt-5 rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
            Ce modèle ne demande aucune variable locale.
          </p>
        ) : (
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            {localScalars.map((variable) => (
              <div key={variable.id}>
                <label htmlFor={`value-${variable.name}`} className={LABEL_CLASS}>
                  {variable.label}
                  <span className="ml-1 font-normal text-slate-400">
                    {variable.value === null ? "(obligatoire)" : "(facultatif)"}
                  </span>
                </label>
                <input
                  id={`value-${variable.name}`}
                  name={variable.name}
                  type={variable.value_type === "date" ? "date" : "text"}
                  inputMode={variable.value_type === "number" ? "decimal" : undefined}
                  value={scalarValue(values, variable.name)}
                  onChange={(event) =>
                    setValues((current) => ({
                      ...current,
                      [variable.name]: event.target.value,
                    }))
                  }
                  className={`mt-1.5 ${FIELD_CLASS}`}
                />
                {variable.description ? (
                  <p className="mt-1 text-xs text-slate-500">{variable.description}</p>
                ) : null}
              </div>
            ))}
          </div>
        )}

        {localProducts.map((variable) => {
          const rows = productDraftRows(values, variable.name);
          return (
            <div
              key={variable.id}
              className="mt-5 rounded-xl border border-slate-200 bg-slate-50/40 p-4"
            >
              <ProductRowsEditor
                rows={rows}
                onChange={(nextRows) =>
                  setValues((current) => ({ ...current, [variable.name]: nextRows }))
                }
                label={variable.label}
              />
              {variable.description ? (
                <p className="mt-1 text-xs text-slate-500">{variable.description}</p>
              ) : null}
            </div>
          );
        })}

        {error ? (
          <div
            role="alert"
            className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-sm text-rose-700"
          >
            <p className="flex items-start gap-2">
              <AlertIcon className="mt-0.5 size-4 shrink-0" />
              {error.message}
            </p>
            {error.log ? (
              <details className="mt-2">
                <summary className="cursor-pointer text-xs font-medium">Voir le journal LaTeX</summary>
                <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded-lg bg-white/70 p-2 text-[11px] leading-relaxed">
                  {error.log}
                </pre>
              </details>
            ) : null}
          </div>
        ) : null}

        {generatedDocument ? (
          <div
            role="status"
            className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-3.5 py-2.5 text-sm text-emerald-700"
          >
            <span className="flex items-start gap-2">
              <CheckIcon className="mt-0.5 size-4 shrink-0" />
              PDF généré : {generatedDocument.filename}
            </span>
            <a
              href={`/api/documents/${generatedDocument.id}/download`}
              className="inline-flex items-center gap-1.5 font-semibold underline-offset-2 hover:underline"
            >
              <DownloadIcon className="size-4" />
              Télécharger
            </a>
          </div>
        ) : null}

        <div className="mt-5 flex flex-wrap justify-end gap-2">
          {isAdmin ? (
            <button
              type="button"
              onClick={openPreview}
              disabled={previewPending || pending}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {previewPending ? "Aperçu…" : "Aperçu du source"}
            </button>
          ) : null}
          <button type="submit" disabled={pending} className={SUBMIT_BUTTON_CLASS}>
            {pending ? "Génération en cours…" : "Générer le PDF"}
          </button>
        </div>
      </form>

      {preview !== null ? (
        <div
          role="presentation"
          onClick={() => setPreview(null)}
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/50 p-4 backdrop-blur-sm sm:p-8"
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="preview-title"
            onClick={(event) => event.stopPropagation()}
            className="w-full max-w-3xl rounded-2xl border border-slate-200 bg-white shadow-xl"
          >
            <header className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
              <div>
                <h2 id="preview-title" className="text-sm font-semibold text-slate-900">
                  Aperçu du source rendu
                </h2>
                <p className="mt-0.5 text-xs text-slate-500">{templateName}</p>
              </div>
              <button
                type="button"
                onClick={() => setPreview(null)}
                className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
                aria-label="Fermer"
              >
                <CloseIcon className="size-5" />
              </button>
            </header>
            <pre className="max-h-[70vh] overflow-auto whitespace-pre-wrap bg-slate-950 p-5 text-xs leading-relaxed text-slate-100">
              {preview}
            </pre>
          </div>
        </div>
      ) : null}
    </>
  );
}
