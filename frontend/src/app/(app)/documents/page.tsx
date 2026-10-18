import Link from "next/link";

import { DownloadIcon, FileTextIcon } from "@/components/icons";
import { apiFetch } from "@/lib/api";
import { formatDateTimeUtc, formatFileSize } from "@/lib/format";
import type { GeneratedDocument } from "@/lib/types";

function formatValue(value: unknown): string {
  if (Array.isArray(value)) {
    return `${value.length} ligne${value.length === 1 ? "" : "s"}`;
  }
  if (
    value !== null &&
    typeof value === "object" &&
    "filename" in value &&
    typeof (value as { filename: unknown }).filename === "string"
  ) {
    return `Image : ${(value as { filename: string }).filename}`;
  }
  if (value === null || value === undefined || typeof value === "object") {
    return "—";
  }
  return String(value);
}

export default async function DocumentsPage() {
  const documents = await apiFetch<GeneratedDocument[]>("/api/v1/documents?limit=50");

  return (
    <div className="space-y-8">
      <header>
        <p className="text-sm font-medium text-teal-700">Documents</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 lg:text-3xl">
          Documents générés
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-500">
          Les 50 derniers PDF produits, avec les valeurs utilisées au moment de la
          génération.
        </p>
      </header>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <header className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Historique</h2>
            <p className="mt-0.5 text-xs text-slate-500">
              {documents.length === 0
                ? "Aucun document généré."
                : `${documents.length} document${documents.length === 1 ? "" : "s"}`}
            </p>
          </div>
          <FileTextIcon className="size-5 text-slate-400" />
        </header>

        {documents.length === 0 ? (
          <p className="px-5 py-10 text-center text-sm text-slate-500">
            Ouvrez un modèle dans « Modèles LaTeX » pour générer un premier document.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-3 font-semibold">Date</th>
                  <th className="px-5 py-3 font-semibold">Modèle</th>
                  <th className="px-5 py-3 font-semibold">Généré par</th>
                  <th className="px-5 py-3 font-semibold">Valeurs</th>
                  <th className="px-5 py-3 font-semibold">Taille</th>
                  <th className="px-5 py-3 text-right font-semibold">PDF</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {documents.map((document) => {
                  const entries = Object.entries(document.values).slice(0, 3);
                  const remaining = Object.keys(document.values).length - entries.length;
                  return (
                    <tr key={document.id} className="align-top">
                      <td className="whitespace-nowrap px-5 py-3 text-slate-600">
                        {formatDateTimeUtc(document.created_at)}
                      </td>
                      <td className="px-5 py-3">
                        {document.template_id ? (
                          <Link
                            href={`/templates/${document.template_id}`}
                            className="font-medium text-slate-900 hover:text-teal-700"
                          >
                            {document.template_name}
                          </Link>
                        ) : (
                          <span className="font-medium text-slate-900">
                            {document.template_name}
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-3 text-slate-600">
                        {document.generated_by_email ?? "—"}
                      </td>
                      <td className="px-5 py-3 text-xs text-slate-600">
                        <ul className="space-y-0.5">
                          {entries.map(([name, value]) => (
                            <li key={name}>
                              <span className="font-mono text-[11px] text-slate-400">
                                {name}
                              </span>{" "}
                              {formatValue(value)}
                            </li>
                          ))}
                          {remaining > 0 ? (
                            <li className="text-slate-400">+{remaining} autre(s)</li>
                          ) : null}
                        </ul>
                      </td>
                      <td className="whitespace-nowrap px-5 py-3 text-slate-600">
                        {formatFileSize(document.size_bytes)}
                      </td>
                      <td className="px-5 py-3 text-right">
                        <a
                          href={`/api/documents/${document.id}/download`}
                          className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-teal-700 transition hover:bg-teal-50"
                        >
                          <DownloadIcon className="size-4" />
                          Télécharger
                        </a>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
