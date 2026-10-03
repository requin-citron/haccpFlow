"use client";

import { useActionState, useEffect, useRef, useState } from "react";

import { saveReadingAction } from "@/actions/readings";
import { AlertIcon, CloseIcon, PencilIcon, PlusIcon } from "@/components/icons";
import { INITIAL_READING_FORM_STATE } from "@/lib/form-state";
import { formatDayLabel } from "@/lib/format";
import type { Equipment, TemperatureReadingDay } from "@/lib/types";

const FIELD_CLASS =
  "w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-teal-500 focus:ring-4 focus:ring-teal-500/15";

export function ReadingDialog({
  equipment,
  readingDate,
  day,
}: {
  equipment: Equipment;
  readingDate: string;
  day: TemperatureReadingDay;
}) {
  const [open, setOpen] = useState(false);
  const [state, formAction, pending] = useActionState(
    saveReadingAction,
    INITIAL_READING_FORM_STATE,
  );
  const formRef = useRef<HTMLFormElement>(null);
  const isComplete = day.morning !== null && day.evening !== null;

  useEffect(() => {
    if (state.status === "success") {
      setOpen(false);
    }
  }, [state]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={
          isComplete
            ? "inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
            : "inline-flex items-center gap-1.5 rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-teal-700"
        }
      >
        {isComplete ? <PencilIcon className="size-4" /> : <PlusIcon className="size-4" />}
        {isComplete ? "Modifier" : "Saisir"}
      </button>

      {open ? (
        <div
          role="presentation"
          onClick={() => setOpen(false)}
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/50 p-4 backdrop-blur-sm sm:p-8"
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="reading-form-title"
            onClick={(event) => event.stopPropagation()}
            className="animate-fade-in w-full max-w-md rounded-2xl border border-slate-200 bg-white shadow-xl"
          >
            <header className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
              <div>
                <h2
                  id="reading-form-title"
                  className="text-lg font-semibold tracking-tight text-slate-900"
                >
                  {equipment.name}
                </h2>
                <p className="mt-0.5 text-sm capitalize text-slate-500">
                  {formatDayLabel(readingDate)}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Fermer"
                className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
              >
                <CloseIcon className="size-5" />
              </button>
            </header>

            <form ref={formRef} action={formAction} className="space-y-5 px-6 py-5">
              <input type="hidden" name="equipment_id" value={equipment.id} />
              <input type="hidden" name="reading_date" value={readingDate} />

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label htmlFor="morning_celsius" className="block text-sm font-medium text-slate-700">
                    Matin (°C)
                  </label>
                  <input
                    id="morning_celsius"
                    name="morning_celsius"
                    type="number"
                    step="0.1"
                    inputMode="decimal"
                    autoFocus
                    defaultValue={day.morning?.temperature_celsius ?? ""}
                    placeholder="—"
                    className={FIELD_CLASS}
                  />
                </div>
                <div className="space-y-1.5">
                  <label htmlFor="evening_celsius" className="block text-sm font-medium text-slate-700">
                    Soir (°C)
                  </label>
                  <input
                    id="evening_celsius"
                    name="evening_celsius"
                    type="number"
                    step="0.1"
                    inputMode="decimal"
                    defaultValue={day.evening?.temperature_celsius ?? ""}
                    placeholder="—"
                    className={FIELD_CLASS}
                  />
                </div>
              </div>

              <p className="text-xs text-slate-500">
                Plage cible : {equipment.min_temperature_celsius} °C à{" "}
                {equipment.max_temperature_celsius} °C. Laisse un champ vide pour ne pas le
                modifier.
              </p>

              {state.status === "error" && state.message ? (
                <p
                  role="alert"
                  className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-sm text-rose-700"
                >
                  <AlertIcon className="mt-0.5 size-4 shrink-0" />
                  <span>{state.message}</span>
                </p>
              ) : null}

              <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  disabled={pending}
                  className="rounded-xl bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {pending ? "Enregistrement…" : "Enregistrer"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  );
}
