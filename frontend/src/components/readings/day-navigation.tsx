"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";

import { addDays, formatDayLabel, todayIso } from "@/lib/format";

const BUTTON_CLASS =
  "grid size-10 place-items-center rounded-xl border border-slate-300 bg-white text-slate-600 transition hover:bg-slate-50 hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 disabled:opacity-50";

export function DayNavigation({ date }: { date: string }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  const goTo = (value: string) => {
    startTransition(() => {
      router.push(`/readings?date=${value}`);
    });
  };

  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => goTo(addDays(date, -1))}
          disabled={pending}
          aria-label="Jour précédent"
          className={BUTTON_CLASS}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} className="size-5">
            <path d="m15 18-6-6 6-6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>

        <div className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-900">
          <span className="capitalize">{formatDayLabel(date)}</span>
        </div>

        <button
          type="button"
          onClick={() => goTo(addDays(date, 1))}
          disabled={pending}
          aria-label="Jour suivant"
          className={BUTTON_CLASS}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} className="size-5">
            <path d="m9 6 6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>

      <label className="sr-only" htmlFor="reading-date">
        Choisir une date
      </label>
      <input
        id="reading-date"
        type="date"
        value={date}
        onChange={(event) => {
          if (event.target.value) {
            goTo(event.target.value);
          }
        }}
        className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm outline-none transition focus:border-teal-500 focus:ring-4 focus:ring-teal-500/15"
      />

      {date !== todayIso() ? (
        <button
          type="button"
          onClick={() => goTo(todayIso())}
          disabled={pending}
          className="rounded-xl border border-teal-200 bg-teal-50 px-3 py-2 text-sm font-medium text-teal-700 transition hover:bg-teal-100 disabled:opacity-50"
        >
          Revenir à aujourd&apos;hui
        </button>
      ) : null}
    </div>
  );
}
