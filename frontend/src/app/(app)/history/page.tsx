import Link from "next/link";

import { HistoryIcon } from "@/components/icons";
import { apiFetch } from "@/lib/api";
import { dayFromIso, formatDayLabel, timeFromIso } from "@/lib/format";
import {
  HISTORY_ACTION_LABELS,
  HISTORY_ACTION_TONES,
  HISTORY_ENTITY_LABELS,
  HISTORY_ENTITY_TONES,
  historyEntryLink,
} from "@/lib/history";
import type { CurrentUser, HistoryEntry } from "@/lib/types";

const LIMIT = 100;

const ENTITY_OPTIONS = [
  { value: "", label: "Toutes les sources" },
  { value: "temperature_reading", label: "Relevés de température" },
  { value: "cleaning_record", label: "Nettoyages" },
  { value: "pasteurisation_phase", label: "Pasteurisation" },
];

const FIELD_CLASS =
  "rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-teal-500 focus:ring-4 focus:ring-teal-500/15";

function AccessDenied() {
  return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50 px-6 py-12 text-center">
      <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-amber-100 text-amber-700">
        <HistoryIcon className="size-6" />
      </span>
      <h1 className="mt-4 text-base font-semibold text-slate-900">
        Historique réservé aux administrateurs
      </h1>
      <p className="mx-auto mt-1 max-w-sm text-sm text-slate-600">
        Ce journal regroupe toutes les modifications du plan de maîtrise sanitaire. Demande à un
        administrateur s&apos;il te le faut.
      </p>
    </div>
  );
}

export default async function HistoryPage({
  searchParams,
}: {
  searchParams: Promise<{ entity?: string; from?: string; to?: string }>;
}) {
  const params = await searchParams;
  const user = await apiFetch<CurrentUser>("/api/v1/auth/me");

  if (user.role !== "admin") {
    return <AccessDenied />;
  }

  const entity = params.entity?.trim() ?? "";
  const from = params.from?.trim() ?? "";
  const to = params.to?.trim() ?? "";

  const query = new URLSearchParams({ limit: String(LIMIT) });
  if (entity) {
    query.set("entity", entity);
  }
  if (from) {
    query.set("from", from);
  }
  if (to) {
    query.set("to", to);
  }

  const entries = await apiFetch<HistoryEntry[]>(`/api/v1/history?${query.toString()}`);

  const groups: { day: string; entries: HistoryEntry[] }[] = [];
  for (const entry of entries) {
    const day = dayFromIso(entry.occurred_at);
    const current = groups.at(-1);
    if (current && current.day === day) {
      current.entries.push(entry);
    } else {
      groups.push({ day, entries: [entry] });
    }
  }

  const filtered = Boolean(entity || from || to);

  return (
    <div className="space-y-8">
      <header>
        <p className="text-sm font-medium text-teal-700">Traçabilité</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 lg:text-3xl">
          Historique
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-500">
          Toutes les modifications enregistrées sur la plateforme, du plus récent au plus ancien :
          relevés de température, nettoyages et pasteurisation. Les corrections y figurent avec
          leur valeur précédente et leur auteur.
        </p>
      </header>

      <form action="/history" method="get" className="flex flex-wrap items-end gap-3">
        <div className="space-y-1.5">
          <label htmlFor="entity" className="block text-xs font-medium text-slate-600">
            Source
          </label>
          <select id="entity" name="entity" defaultValue={entity} className={FIELD_CLASS}>
            {ENTITY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
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
          Filtrer
        </button>
        {filtered ? (
          <Link
            href="/history"
            className="rounded-xl border border-teal-200 bg-teal-50 px-4 py-2.5 text-sm font-medium text-teal-700 transition hover:bg-teal-100"
          >
            Réinitialiser
          </Link>
        ) : null}
      </form>

      <p className="text-xs text-slate-500">
        {entries.length} modification{entries.length > 1 ? "s" : ""} affichée
        {entries.length > 1 ? "s" : ""} · heures en UTC
        {entries.length === LIMIT ? ` · limité aux ${LIMIT} plus récentes` : ""}
      </p>

      {entries.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white/60 px-6 py-16 text-center">
          <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-slate-100 text-slate-500">
            <HistoryIcon className="size-6" />
          </span>
          <h2 className="mt-4 text-base font-semibold text-slate-900">
            Aucune modification à afficher
          </h2>
          <p className="mx-auto mt-1 max-w-sm text-sm text-slate-500">
            {filtered
              ? "Aucune entrée ne correspond à ces critères."
              : "Les saisies et corrections apparaîtront ici au fur et à mesure."}
          </p>
        </div>
      ) : (
        <div className="space-y-8">
          {groups.map((group) => (
            <section key={group.day} className="space-y-3">
              <h2 className="flex items-center gap-3 text-sm font-semibold text-slate-700">
                <span className="capitalize">{formatDayLabel(group.day)}</span>
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
                  {group.entries.length}
                </span>
              </h2>
              <ol className="space-y-3">
                {group.entries.map((entry) => {
                  const link = historyEntryLink(entry);
                  return (
                    <li
                      key={entry.id}
                      className="flex gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
                    >
                      <span
                        className={`h-fit shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-medium ring-1 ring-inset ${HISTORY_ENTITY_TONES[entry.entity]}`}
                      >
                        {HISTORY_ENTITY_LABELS[entry.entity]}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-baseline gap-2">
                          {link === null ? (
                            <span className="font-medium text-slate-900">{entry.subject}</span>
                          ) : (
                            <Link
                              href={link}
                              className="font-medium text-slate-900 transition hover:text-teal-700"
                            >
                              {entry.subject}
                            </Link>
                          )}
                          <span
                            className={`text-xs font-semibold ${HISTORY_ACTION_TONES[entry.action]}`}
                          >
                            {HISTORY_ACTION_LABELS[entry.action]}
                          </span>
                        </div>
                        <p className="mt-0.5 text-xs text-slate-500">
                          {entry.detail}
                          {entry.actor_email ? ` · ${entry.actor_email}` : ""}
                        </p>
                        {entry.changes.length > 0 ? (
                          <ul className="mt-2 space-y-1">
                            {entry.changes.map((change) => (
                              <li
                                key={change.field}
                                className="rounded-lg bg-slate-50 px-2.5 py-1.5 text-[11px] text-slate-600"
                              >
                                <span className="font-medium text-slate-700">{change.label}</span>{" "}
                                <span className="text-slate-400">{change.previous ?? "—"}</span>
                                {" → "}
                                <span className="text-slate-800">{change.new ?? "—"}</span>
                              </li>
                            ))}
                          </ul>
                        ) : null}
                      </div>
                      <span className="shrink-0 text-xs tabular-nums text-slate-400">
                        {timeFromIso(entry.occurred_at)}
                      </span>
                    </li>
                  );
                })}
              </ol>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
