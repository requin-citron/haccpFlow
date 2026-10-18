"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import {
  AlertIcon,
  CheckIcon,
  PencilIcon,
  PlusIcon,
  TrashIcon,
} from "@/components/icons";
import {
  ProductRowsEditor,
  productRowsFromValue,
  productRowsToPayload,
  validateProductRows,
  type ProductRowDraft,
} from "@/components/templates/product-rows-editor";
import { FIELD_CLASS, LABEL_CLASS } from "@/lib/ui";
import type {
  TemplateVariable,
  TemplateVariableKind,
  TemplateVariableValueType,
} from "@/lib/types";

type Draft = {
  name: string;
  label: string;
  description: string;
  kind: TemplateVariableKind;
  valueType: TemplateVariableValueType;
  value: string;
  rows: ProductRowDraft[];
};

type ErrorPayload = {
  code?: string;
  detail?: string;
  context?: Record<string, unknown> | null;
};

const EMPTY_DRAFT: Draft = {
  name: "",
  label: "",
  description: "",
  kind: "local",
  valueType: "text",
  value: "",
  rows: [],
};

const KIND_LABELS: Record<TemplateVariableKind, string> = {
  static: "Statique",
  local: "Locale",
};

const TYPE_LABELS: Record<TemplateVariableValueType, string> = {
  text: "Texte",
  number: "Nombre",
  date: "Date",
  products: "Lignes produits",
};

function describeError(payload: ErrorPayload | null): string {
  switch (payload?.code) {
    case "template_variable_name_taken":
      return "Ce nom de variable est déjà utilisé sur ce modèle.";
    case "template_variable_invalid":
      return payload.detail ?? "La variable est invalide.";
    case "template_value_invalid":
      return payload.detail ?? "La valeur est invalide.";
    default:
      return payload?.detail ?? "L'enregistrement a échoué. Réessaie dans un instant.";
  }
}

function draftFrom(variable: TemplateVariable): Draft {
  return {
    name: variable.name,
    label: variable.label,
    description: variable.description ?? "",
    kind: variable.kind,
    valueType: variable.value_type,
    value: typeof variable.value === "string" ? variable.value : "",
    rows: productRowsFromValue(variable.value),
  };
}

export function VariableEditor({
  templateId,
  variables,
}: {
  templateId: string;
  variables: TemplateVariable[];
}) {
  const router = useRouter();
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  function reset(): void {
    setDraft(EMPTY_DRAFT);
    setEditingId(null);
    setError(null);
  }

  function update<K extends keyof Draft>(key: K, value: Draft[K]): void {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    if (!draft.name.trim() || !draft.label.trim()) {
      setError("Le nom Jinja et le libellé sont obligatoires.");
      return;
    }
    const isProducts = draft.valueType === "products";
    if (draft.kind === "static" && !isProducts && !draft.value.trim()) {
      setError("Une variable statique doit avoir une valeur.");
      return;
    }
    if (isProducts) {
      const rowsError = validateProductRows(draft.rows);
      if (rowsError) {
        setError(rowsError);
        return;
      }
    }

    const payload = {
      name: draft.name.trim(),
      label: draft.label.trim(),
      description: draft.description.trim() || null,
      kind: draft.kind,
      value_type: draft.valueType,
      value: isProducts
        ? productRowsToPayload(draft.rows)
        : draft.value.trim()
          ? draft.value
          : null,
    };
    const endpoint = editingId
      ? `/api/templates/${templateId}/variables/${editingId}`
      : `/api/templates/${templateId}/variables`;

    setPending(true);
    try {
      const response = await fetch(endpoint, {
        method: editingId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as ErrorPayload | null;
        setError(describeError(body));
        return;
      }
      setSuccess(editingId ? "Variable mise à jour." : "Variable créée.");
      reset();
      router.refresh();
    } catch {
      setError("Impossible de joindre le serveur. Réessaie dans un instant.");
    } finally {
      setPending(false);
    }
  }

  async function remove(variable: TemplateVariable): Promise<void> {
    const warning = variable.used_in_template
      ? `La variable « ${variable.name} » est utilisée dans le template. La supprimer cassera les prochaines générations. Continuer ?`
      : `Supprimer la variable « ${variable.name} » ?`;
    if (!window.confirm(warning)) {
      return;
    }
    setError(null);
    setSuccess(null);
    setPending(true);
    try {
      const response = await fetch(
        `/api/templates/${templateId}/variables/${variable.id}`,
        { method: "DELETE" },
      );
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as ErrorPayload | null;
        setError(describeError(body));
        return;
      }
      if (editingId === variable.id) {
        reset();
      }
      setSuccess("Variable supprimée.");
      router.refresh();
    } catch {
      setError("Impossible de joindre le serveur. Réessaie dans un instant.");
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">Variables du modèle</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            Les variables statiques sont intégrées à la génération ; les locales sont
            demandées à l&apos;opérateur.
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Syntaxe Jinja : <code className="font-mono">&lt;&lt; nom &gt;&gt;</code> pour
            une variable, <code className="font-mono">&lt;% if … %&gt;</code> pour un bloc.
            Les accolades LaTeX restent littérales.
          </p>
        </div>
        <button
          type="button"
          onClick={reset}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50"
        >
          <PlusIcon className="size-4" />
          Nouvelle variable
        </button>
      </header>

      <form onSubmit={submit} className="border-b border-slate-100 bg-slate-50/60 px-5 py-4">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <label htmlFor="variable-name" className={LABEL_CLASS}>
              Nom Jinja
            </label>
            <input
              id="variable-name"
              value={draft.name}
              onChange={(event) => update("name", event.target.value)}
              maxLength={64}
              placeholder="client_nom"
              className={`mt-1.5 font-mono ${FIELD_CLASS}`}
            />
          </div>
          <div>
            <label htmlFor="variable-label" className={LABEL_CLASS}>
              Libellé affiché
            </label>
            <input
              id="variable-label"
              value={draft.label}
              onChange={(event) => update("label", event.target.value)}
              maxLength={120}
              placeholder="Nom du client"
              className={`mt-1.5 ${FIELD_CLASS}`}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="variable-kind" className={LABEL_CLASS}>
                Nature
              </label>
              <select
                id="variable-kind"
                value={draft.kind}
                onChange={(event) =>
                  update("kind", event.target.value as TemplateVariableKind)
                }
                className={`mt-1.5 ${FIELD_CLASS}`}
              >
                <option value="local">Locale</option>
                <option value="static">Statique</option>
              </select>
            </div>
            <div>
              <label htmlFor="variable-type" className={LABEL_CLASS}>
                Type
              </label>
              <select
                id="variable-type"
                value={draft.valueType}
                onChange={(event) =>
                  update("valueType", event.target.value as TemplateVariableValueType)
                }
                className={`mt-1.5 ${FIELD_CLASS}`}
              >
                <option value="text">Texte</option>
                <option value="number">Nombre</option>
                <option value="date">Date</option>
                <option value="products">Lignes produits</option>
              </select>
            </div>
          </div>
          {draft.valueType !== "products" ? (
            <div>
              <label htmlFor="variable-value" className={LABEL_CLASS}>
                {draft.kind === "static" ? "Valeur" : "Valeur par défaut"}
              </label>
              <input
                id="variable-value"
                type={draft.valueType === "date" ? "date" : "text"}
                inputMode={draft.valueType === "number" ? "decimal" : undefined}
                value={draft.value}
                onChange={(event) => update("value", event.target.value)}
                placeholder={draft.kind === "static" ? "Obligatoire" : "Facultative"}
                className={`mt-1.5 ${FIELD_CLASS}`}
              />
            </div>
          ) : null}
          {draft.valueType === "products" ? (
            <div className="sm:col-span-2 lg:col-span-3">
              <ProductRowsEditor
                rows={draft.rows}
                onChange={(rows) => update("rows", rows)}
                label={draft.kind === "static" ? "Lignes fixes" : "Lignes par défaut"}
              />
            </div>
          ) : null}
          <div className="sm:col-span-2">
            <label htmlFor="variable-description" className={LABEL_CLASS}>
              Description <span className="font-normal text-slate-400">(facultative)</span>
            </label>
            <input
              id="variable-description"
              value={draft.description}
              onChange={(event) => update("description", event.target.value)}
              maxLength={500}
              className={`mt-1.5 ${FIELD_CLASS}`}
            />
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

        <div className="mt-4 flex flex-wrap justify-end gap-2">
          {editingId ? (
            <button
              type="button"
              onClick={reset}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
            >
              Annuler
            </button>
          ) : null}
          <button
            type="submit"
            disabled={pending}
            className="rounded-xl bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {pending
              ? "Enregistrement…"
              : editingId
                ? "Enregistrer la variable"
                : "Créer la variable"}
          </button>
        </div>
      </form>

      {variables.length === 0 ? (
        <p className="px-5 py-8 text-center text-sm text-slate-500">
          Aucune variable déclarée pour ce modèle.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px] text-left text-sm">
            <thead className="bg-white text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-5 py-3 font-semibold">Nom</th>
                <th className="px-5 py-3 font-semibold">Libellé</th>
                <th className="px-5 py-3 font-semibold">Nature</th>
                <th className="px-5 py-3 font-semibold">Type</th>
                <th className="px-5 py-3 font-semibold">Valeur / défaut</th>
                <th className="px-5 py-3 font-semibold">Usage</th>
                <th className="px-5 py-3 text-right font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {variables.map((variable) => (
                <tr key={variable.id}>
                  <td className="px-5 py-3 font-mono text-xs text-slate-700">
                    {variable.name}
                  </td>
                  <td className="px-5 py-3 text-slate-900">{variable.label}</td>
                  <td className="px-5 py-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        variable.kind === "static"
                          ? "bg-indigo-50 text-indigo-700"
                          : "bg-sky-50 text-sky-700"
                      }`}
                    >
                      {KIND_LABELS[variable.kind]}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-slate-600">
                    {TYPE_LABELS[variable.value_type]}
                  </td>
                  <td className="px-5 py-3 text-slate-600">
                    {variable.value_type === "products" ? (
                      `${Array.isArray(variable.value) ? variable.value.length : 0} ligne(s)`
                    ) : typeof variable.value === "string" && variable.value ? (
                      variable.value
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                  <td className="px-5 py-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        variable.used_in_template
                          ? "bg-emerald-50 text-emerald-700"
                          : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {variable.used_in_template ? "Utilisée" : "Non utilisée"}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex justify-end gap-1">
                      <button
                        type="button"
                        onClick={() => {
                          setDraft(draftFrom(variable));
                          setEditingId(variable.id);
                          setError(null);
                          setSuccess(null);
                        }}
                        className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
                      >
                        <PencilIcon className="size-3.5" />
                        Modifier
                      </button>
                      <button
                        type="button"
                        onClick={() => remove(variable)}
                        disabled={pending}
                        className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-rose-600 transition hover:bg-rose-50 disabled:opacity-50"
                      >
                        <TrashIcon className="size-3.5" />
                        Supprimer
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
