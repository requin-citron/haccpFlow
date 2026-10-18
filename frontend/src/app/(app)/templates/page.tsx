import Link from "next/link";

import { DownloadIcon, FileTextIcon } from "@/components/icons";
import { UploadTemplateForm } from "@/components/templates/upload-template-form";
import { apiFetch } from "@/lib/api";
import { formatDateTimeUtc, formatFileSize } from "@/lib/format";
import type { CurrentUser, LatexTemplate } from "@/lib/types";

export default async function TemplatesPage() {
  const user = await apiFetch<CurrentUser>("/api/v1/auth/me");
  const isAdmin = user.role === "admin";
  const templates = await apiFetch<LatexTemplate[]>("/api/v1/templates");

  return (
    <div className="space-y-8">
      <header>
        <p className="text-sm font-medium text-teal-700">
          {isAdmin ? "Administration" : "Documents"}
        </p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 lg:text-3xl">
          Modèles LaTeX
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-500">
          {isAdmin
            ? "Importez les sources .tex, configurez leurs variables puis générez les documents. Le fichier source est stocké sous un identifiant unique."
            : "Choisissez un modèle pour saisir les valeurs locales et générer un PDF."}
        </p>
      </header>

      {isAdmin ? <UploadTemplateForm /> : null}

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <header className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Modèles disponibles</h2>
            <p className="mt-0.5 text-xs text-slate-500">
              {templates.length === 0
                ? "Aucun modèle pour le moment."
                : `${templates.length} modèle${templates.length === 1 ? "" : "s"}`}
            </p>
          </div>
          <FileTextIcon className="size-5 text-slate-400" />
        </header>

        {templates.length === 0 ? (
          <p className="px-5 py-10 text-center text-sm text-slate-500">
            {isAdmin
              ? "Envoyez un premier fichier .tex avec le formulaire ci-dessus."
              : "Aucun modèle n'est encore disponible."}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-3 font-semibold">Nom</th>
                  <th className="px-5 py-3 font-semibold">Fichier d&apos;origine</th>
                  <th className="px-5 py-3 font-semibold">Taille</th>
                  <th className="px-5 py-3 font-semibold">Ajouté par</th>
                  <th className="px-5 py-3 font-semibold">Date</th>
                  <th className="px-5 py-3 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {templates.map((template) => (
                  <tr key={template.id} className="align-middle">
                    <td className="px-5 py-3 font-medium text-slate-900">{template.name}</td>
                    <td className="px-5 py-3 font-mono text-xs text-slate-600">
                      {template.original_filename}
                    </td>
                    <td className="px-5 py-3 text-slate-600">
                      {formatFileSize(template.size_bytes)}
                    </td>
                    <td className="px-5 py-3 text-slate-600">
                      {template.uploaded_by_email ?? "—"}
                    </td>
                    <td className="px-5 py-3 text-slate-600">
                      {formatDateTimeUtc(template.created_at)}
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center justify-end gap-2">
                        {isAdmin ? (
                          <a
                            href={`/api/templates/${template.id}/download`}
                            className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
                          >
                            <DownloadIcon className="size-4" />
                            Source
                          </a>
                        ) : null}
                        <Link
                          href={`/templates/${template.id}`}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-teal-50 px-2.5 py-1.5 text-xs font-semibold text-teal-700 transition hover:bg-teal-100"
                        >
                          <FileTextIcon className="size-4" />
                          Ouvrir
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
