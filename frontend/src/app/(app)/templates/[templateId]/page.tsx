import Link from "next/link";
import { notFound } from "next/navigation";

import { DownloadIcon, FileTextIcon } from "@/components/icons";
import { GenerateTemplateForm } from "@/components/templates/generate-template-form";
import { VariableEditor } from "@/components/templates/variable-editor";
import { apiFetch } from "@/lib/api";
import { formatDateTimeUtc, formatFileSize } from "@/lib/format";
import type { CurrentUser, LatexTemplate, TemplateVariable } from "@/lib/types";

export default async function TemplatePage({
  params,
}: {
  params: Promise<{ templateId: string }>;
}) {
  const { templateId } = await params;
  const user = await apiFetch<CurrentUser>("/api/v1/auth/me");
  const isAdmin = user.role === "admin";
  const templates = await apiFetch<LatexTemplate[]>("/api/v1/templates");
  const template = templates.find((item) => item.id === templateId);

  if (!template) {
    notFound();
  }

  const variables = await apiFetch<TemplateVariable[]>(
    `/api/v1/templates/${templateId}/variables`,
  );
  const localVariableCount = variables.filter(
    (variable) => variable.kind === "local",
  ).length;

  return (
    <div className="space-y-8">
      <header>
        <Link
          href="/templates"
          className="text-sm font-medium text-teal-700 hover:text-teal-800"
        >
          ← Modèles LaTeX
        </Link>
        <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900 lg:text-3xl">
              {template.name}
            </h1>
            <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-slate-500">
              <span className="font-mono text-xs">{template.original_filename}</span>
              <span>·</span>
              <span>{formatFileSize(template.size_bytes)}</span>
              <span>·</span>
              <span>{formatDateTimeUtc(template.created_at)}</span>
              {template.uploaded_by_email ? (
                <>
                  <span>·</span>
                  <span>{template.uploaded_by_email}</span>
                </>
              ) : null}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {isAdmin ? (
              <a
                href={`/api/templates/${template.id}/download`}
                className="inline-flex items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
              >
                <DownloadIcon className="size-4" />
                Télécharger le source
              </a>
            ) : null}
            <span className="inline-flex items-center gap-1.5 rounded-xl bg-slate-100 px-3.5 py-2 text-sm font-medium text-slate-600">
              <FileTextIcon className="size-4" />
              {localVariableCount} variable{localVariableCount === 1 ? "" : "s"} locale
              {localVariableCount === 1 ? "" : "s"}
            </span>
          </div>
        </div>
      </header>

      <GenerateTemplateForm
        templateId={template.id}
        templateName={template.name}
        variables={variables}
        isAdmin={isAdmin}
      />

      {isAdmin ? (
        <VariableEditor templateId={template.id} variables={variables} />
      ) : null}
    </div>
  );
}
