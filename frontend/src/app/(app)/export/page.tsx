import Link from "next/link";

import {
  DownloadIcon,
  DropletIcon,
  FlameIcon,
  ThermometerIcon,
  TruckIcon,
} from "@/components/icons";

const FIELD_CLASS =
  "rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 shadow-sm outline-none transition focus:border-teal-500 focus:ring-4 focus:ring-teal-500/15";

const DATASETS = [
  {
    key: "readings",
    title: "Relevés de température",
    description:
      "Une ligne par créneau : matériel, date, température, conformité, source et statut du matériel.",
    tone: "bg-sky-50 text-sky-600",
    icon: <ThermometerIcon className="size-5" />,
  },
  {
    key: "cleanings",
    title: "Nettoyages",
    description:
      "Chaque nettoyage déclaré : plan, fréquence, produits, date, commentaire et auteur de la déclaration.",
    tone: "bg-teal-50 text-teal-600",
    icon: <DropletIcon className="size-5" />,
  },
  {
    key: "pasteurisations",
    title: "Pasteurisation",
    description:
      "Un lot par ligne, avec les trois phases en colonnes : heures, température cible, durée calculée et observations.",
    tone: "bg-orange-50 text-orange-600",
    icon: <FlameIcon className="size-5" />,
  },
  {
    key: "transports",
    title: "Transports",
    description:
      "Un déplacement par ligne : véhicule, plaque, lieu, produit et les deux relevés de chaîne du froid.",
    tone: "bg-indigo-50 text-indigo-600",
    icon: <TruckIcon className="size-5" />,
  },
];

export default async function ExportPage({
  searchParams,
}: {
  searchParams: Promise<{ from?: string; to?: string }>;
}) {
  const params = await searchParams;
  const from = params.from?.trim() ?? "";
  const to = params.to?.trim() ?? "";

  const query = new URLSearchParams();
  if (from) {
    query.set("from", from);
  }
  if (to) {
    query.set("to", to);
  }
  const suffix = query.size > 0 ? `?${query.toString()}` : "";
  const filtered = Boolean(from || to);

  return (
    <div className="space-y-8">
      <header>
        <p className="text-sm font-medium text-teal-700">Traçabilité</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 lg:text-3xl">
          Export
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-500">
          Des extractions CSV prêtes à ouvrir dans Excel, à remettre lors d&apos;un contrôle ou à
          archiver. Les éléments désactivés sont conservés, avec leur statut, pour que l&apos;archive
          reste complète.
        </p>
      </header>

      <form
        action="/export"
        method="get"
        className="flex flex-wrap items-end gap-3 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm"
      >
        <div className="space-y-1.5">
          <label htmlFor="from" className="block text-xs font-medium text-slate-600">
            Du
          </label>
          <input id="from" name="from" type="date" defaultValue={from} className={FIELD_CLASS} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="to" className="block text-xs font-medium text-slate-600">
            Au
          </label>
          <input id="to" name="to" type="date" defaultValue={to} className={FIELD_CLASS} />
        </div>
        <button
          type="submit"
          className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50"
        >
          Appliquer la période
        </button>
        {filtered ? (
          <Link
            href="/export"
            className="rounded-xl border border-teal-200 bg-teal-50 px-4 py-2.5 text-sm font-medium text-teal-700 transition hover:bg-teal-100"
          >
            Toute la période
          </Link>
        ) : null}
      </form>

      <p className="text-xs text-slate-500">
        {filtered
          ? `Période appliquée : du ${from || "début"} au ${to || "aujourd'hui"}.`
          : "Sans période précisée, chaque fichier contient tout l'historique — ce qu'il faut pour un archivage complet."}
      </p>

      <section className="grid gap-4 lg:grid-cols-2">
        {DATASETS.map((dataset) => (
          <article
            key={dataset.key}
            className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <header className="flex items-start gap-3">
              <span
                className={`grid size-10 shrink-0 place-items-center rounded-xl ${dataset.tone}`}
              >
                {dataset.icon}
              </span>
              <div className="min-w-0 flex-1">
                <h2 className="font-semibold text-slate-900">{dataset.title}</h2>
                <p className="mt-0.5 text-xs text-slate-500">{dataset.description}</p>
              </div>
            </header>

            <footer className="mt-auto border-t border-slate-100 pt-4">
              <a
                href={`/api/exports/${dataset.key}${suffix}`}
                className="inline-flex items-center gap-2 rounded-xl bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700"
              >
                <DownloadIcon className="size-4" />
                Télécharger le CSV
              </a>
            </footer>
          </article>
        ))}
      </section>

      <p className="text-xs text-slate-500">
        Format : séparateur point-virgule, dates au format français et encodage UTF-8 avec BOM,
        pour une ouverture directe dans Excel.
      </p>
    </div>
  );
}
