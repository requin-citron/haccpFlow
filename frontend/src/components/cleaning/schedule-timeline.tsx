import { DeclareCleaningDialog } from "@/components/cleaning/declare-cleaning-dialog";
import { CheckIcon } from "@/components/icons";
import {
  CLEANING_FREQUENCY_LABELS,
  daysBetween,
  formatRelativeDue,
  formatShortDay,
} from "@/lib/format";
import type { CleaningScheduleEntry, CleaningStatus } from "@/lib/types";

const TONES: Record<CleaningStatus, { card: string; rank: string; badge: string }> = {
  overdue: {
    card: "border-rose-200 bg-rose-50/40",
    rank: "bg-rose-100 text-rose-700",
    badge: "bg-rose-100 text-rose-700 ring-rose-200",
  },
  due_today: {
    card: "border-amber-200 bg-amber-50/40",
    rank: "bg-amber-100 text-amber-700",
    badge: "bg-amber-100 text-amber-700 ring-amber-200",
  },
  upcoming: {
    card: "border-slate-200 bg-white",
    rank: "bg-slate-100 text-slate-600",
    badge: "bg-slate-100 text-slate-600 ring-slate-200",
  },
};

function urgencyLabel(entry: CleaningScheduleEntry, today: string): string {
  if (entry.status === "overdue") {
    return `En retard de ${entry.days_late} j`;
  }
  return formatRelativeDue(entry.next_due_date, today).replace(/^./, (char) =>
    char.toUpperCase(),
  );
}

function ScheduleRow({
  entry,
  today,
  rank,
}: {
  entry: CleaningScheduleEntry;
  today: string;
  rank: number;
}) {
  const tone = TONES[entry.status];
  return (
    <li className={`flex items-center gap-4 rounded-2xl border p-4 shadow-sm ${tone.card}`}>
      <span
        className={`grid size-8 shrink-0 place-items-center rounded-full text-sm font-semibold tabular-nums ${tone.rank}`}
      >
        {rank}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="truncate font-medium text-slate-900">{entry.name}</h3>
          <span
            className={`rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset ${tone.badge}`}
          >
            {urgencyLabel(entry, today)}
          </span>
        </div>
        <p className="mt-0.5 text-xs text-slate-500">
          {CLEANING_FREQUENCY_LABELS[entry.frequency]} · échéance le{" "}
          {formatShortDay(entry.next_due_date)}
          {entry.last_cleaning_date
            ? ` · dernier nettoyage le ${formatShortDay(entry.last_cleaning_date)}`
            : " · jamais nettoyé"}
        </p>
        {entry.products ? (
          <p className="mt-1 text-xs text-slate-500">{entry.products}</p>
        ) : null}
      </div>
      <div className="shrink-0">
        <DeclareCleaningDialog
          plan={{ id: entry.plan_id, name: entry.name }}
          defaultDate={today}
          compact
        />
      </div>
    </li>
  );
}

export function NextCleaningCard({
  entry,
  today,
}: {
  entry: CleaningScheduleEntry;
  today: string;
}) {
  const late = entry.status === "overdue";
  const soon = entry.status === "due_today";

  return (
    <section
      className={`rounded-2xl border-2 p-6 shadow-sm ${
        late
          ? "border-rose-200 bg-rose-50/60"
          : soon
            ? "border-amber-200 bg-amber-50/60"
            : "border-teal-200 bg-teal-50/50"
      }`}
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        Prochain nettoyage
      </p>
      <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">{entry.name}</h2>
          <p className="mt-1 text-sm text-slate-600">
            {CLEANING_FREQUENCY_LABELS[entry.frequency]} · échéance{" "}
            <span className="font-medium">{formatRelativeDue(entry.next_due_date, today)}</span> (
            {formatShortDay(entry.next_due_date)})
            {entry.last_cleaning_date
              ? ` · dernier nettoyage le ${formatShortDay(entry.last_cleaning_date)}`
              : " · jamais nettoyé"}
          </p>
          {entry.products ? (
            <p className="mt-2 text-sm text-slate-600">
              <span className="font-medium text-slate-700">Produits :</span> {entry.products}
            </p>
          ) : null}
        </div>
        <DeclareCleaningDialog plan={{ id: entry.plan_id, name: entry.name }} defaultDate={today} />
      </div>
    </section>
  );
}

export function ScheduleTimeline({
  entries,
  today,
  startRank = 1,
}: {
  entries: CleaningScheduleEntry[];
  today: string;
  startRank?: number;
}) {
  if (entries.length === 0) {
    return (
      <div className="flex items-center gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-800">
        <CheckIcon className="size-5 shrink-0" />
        Rien de planifié pour les prochains jours.
      </div>
    );
  }

  return (
    <ol className="space-y-3">
      {entries.map((entry, index) => (
        <ScheduleRow
          key={entry.plan_id}
          entry={entry}
          today={today}
          rank={startRank + index}
        />
      ))}
    </ol>
  );
}

export function groupByUrgency(
  entries: CleaningScheduleEntry[],
): { status: CleaningStatus; title: string; entries: CleaningScheduleEntry[] }[] {
  const overdue = entries.filter((entry) => entry.status === "overdue");
  const dueToday = entries.filter((entry) => entry.status === "due_today");
  const upcoming = [...entries]
    .filter((entry) => entry.status === "upcoming")
    .sort((first, second) => daysBetween(second.next_due_date, first.next_due_date));

  return [
    { status: "overdue" as const, title: "En retard", entries: overdue },
    { status: "due_today" as const, title: "Aujourd'hui", entries: dueToday },
    { status: "upcoming" as const, title: "À venir", entries: upcoming },
  ].filter((group) => group.entries.length > 0);
}
