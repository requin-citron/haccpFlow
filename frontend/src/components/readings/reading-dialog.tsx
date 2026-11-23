"use client";

import { useActionState, useEffect, useState } from "react";

import { saveReadingAction } from "@/actions/readings";
import { AlertIcon, CloseIcon, PencilIcon, PlusIcon } from "@/components/icons";
import { useI18n } from "@/components/locale-provider";
import { INITIAL_READING_FORM_STATE } from "@/lib/form-state";
import { formatDayLabel, formatTemperature } from "@/lib/format";
import type { Locale } from "@/lib/i18n";
import {
  parseTemperatureInput,
  readingAction,
  type ParsedTemperature,
  type TemperatureField,
} from "@/lib/readings";
import { CANCEL_BUTTON_CLASS, FIELD_CLASS, ICON_BUTTON_CLASS, SUBMIT_BUTTON_CLASS } from "@/lib/ui";
import type {
  Equipment,
  TemperatureReadingCorrection,
  TemperatureReadingDay,
  TemperatureReadingSlot,
} from "@/lib/types";

type SlotDraft = {
  value: string;
  justification: string;
};

function initialDraft(
  slot: TemperatureReadingSlot | null,
  correction: TemperatureReadingCorrection | null,
): SlotDraft {
  return {
    value: slot === null ? "" : String(slot.temperature_celsius),
    justification: correction?.justification ?? "",
  };
}

function hasChanged(
  draft: SlotDraft,
  parsed: ParsedTemperature,
  effective: TemperatureReadingSlot | null,
): boolean {
  if (parsed.kind !== "valid") {
    return false;
  }
  return effective === null || effective.temperature_celsius !== parsed.value;
}

function SlotEditor({
  field,
  label,
  draft,
  effective,
  original,
  modified,
  locale,
  error,
  required,
  autoFocus,
  onChange,
  onJustificationChange,
}: {
  field: TemperatureField;
  label: string;
  draft: SlotDraft;
  effective: TemperatureReadingSlot | null;
  original: TemperatureReadingSlot | null;
  modified: TemperatureReadingCorrection | null;
  locale: Locale;
  error?: string;
  required: boolean;
  autoFocus: boolean;
  onChange: (value: string) => void;
  onJustificationChange: (value: string) => void;
}) {
  const { t } = useI18n();
  const inputId = `${field}_celsius`;
  const justificationId = `${field}_justification`;
  const helperId = `${field}_reading_help`;
  const errorId = `${field}_reading_error`;
  const parsed = parseTemperatureInput(draft.value);
  const invalid = parsed.kind === "invalid";
  const describedBy = [
    effective !== null ? helperId : null,
    error ? errorId : null,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <fieldset
      data-reading-slot={field}
      className="min-w-0 space-y-3 rounded-2xl border border-slate-200 bg-slate-50/60 p-3.5"
    >
      <div className="flex items-center justify-between gap-2">
        <label htmlFor={inputId} className="text-sm font-semibold text-slate-800">
          {label}
        </label>
        {modified ? (
          <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-700 ring-1 ring-inset ring-amber-200">
            {t("Corrigé")}
          </span>
        ) : null}
      </div>

      <input
        id={inputId}
        name={inputId}
        type="number"
        step="0.1"
        inputMode="decimal"
        autoFocus={autoFocus}
        value={draft.value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="—"
        aria-invalid={invalid || error ? true : undefined}
        aria-describedby={describedBy || undefined}
        className={`${FIELD_CLASS} text-base sm:text-sm`}
      />

      {effective !== null ? (
        <p id={helperId} className="text-xs text-slate-500">
          {modified && original
            ? t("Mesure originale : {original} · valeur actuelle : {current}", {
                original: formatTemperature(locale, original.temperature_celsius),
                current: formatTemperature(locale, effective.temperature_celsius),
              })
            : t("Valeur actuelle : {current}", {
                current: formatTemperature(locale, effective.temperature_celsius),
              })}
        </p>
      ) : null}

      {required ? (
        <div className="space-y-2 rounded-xl border border-amber-200 bg-amber-50 p-3">
          <label htmlFor={justificationId} className="block text-sm font-medium text-amber-950">
            {field === "morning" ? t("Justification du matin") : t("Justification du soir")}
          </label>
          <textarea
            id={justificationId}
            name={justificationId}
            value={draft.justification}
            onChange={(event) => onJustificationChange(event.target.value)}
            required
            rows={3}
            maxLength={2000}
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? errorId : undefined}
            className={`${FIELD_CLASS} resize-y text-base sm:text-sm`}
          />
          <p className="text-xs text-amber-800">
            {t(
              "La justification sera enregistrée avec cette correction. Seule la dernière correction du créneau est conservée.",
            )}
          </p>
          {modified ? (
            <p className="text-xs text-amber-700">
              {t("La justification précédente est reprise ; modifie-la si nécessaire.")}
            </p>
          ) : null}
        </div>
      ) : null}

      {error ? (
        <p id={errorId} role="alert" className="text-xs font-medium text-rose-700">
          {error}
        </p>
      ) : null}
    </fieldset>
  );
}

export function ReadingDialog({
  equipment,
  readingDate,
  day,
}: {
  equipment: Equipment;
  readingDate: string;
  day: TemperatureReadingDay;
}) {
  const { locale, t } = useI18n();
  const [open, setOpen] = useState(false);
  const [morning, setMorning] = useState<SlotDraft>(() =>
    initialDraft(day.morning, day.morning_modified),
  );
  const [evening, setEvening] = useState<SlotDraft>(() =>
    initialDraft(day.evening, day.evening_modified),
  );
  const [state, formAction, pending] = useActionState(
    saveReadingAction,
    INITIAL_READING_FORM_STATE,
  );
  const action = readingAction(day);

  useEffect(() => {
    if (state.status === "success") {
      setOpen(false);
    }
  }, [state]);

  useEffect(() => {
    if (!open) {
      return;
    }
    setMorning(initialDraft(day.morning, day.morning_modified));
    setEvening(initialDraft(day.evening, day.evening_modified));
  }, [
    open,
    day.morning,
    day.morning_modified,
    day.evening,
    day.evening_modified,
  ]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const morningParsed = parseTemperatureInput(morning.value);
  const eveningParsed = parseTemperatureInput(evening.value);
  const morningChanged = hasChanged(morning, morningParsed, day.morning);
  const eveningChanged = hasChanged(evening, eveningParsed, day.evening);
  const morningRequiresJustification = day.morning !== null && morningChanged;
  const eveningRequiresJustification = day.evening !== null && eveningChanged;
  const morningMissingJustification =
    morningRequiresJustification && morning.justification.trim() === "";
  const eveningMissingJustification =
    eveningRequiresJustification && evening.justification.trim() === "";
  const invalidValues =
    morningParsed.kind === "invalid" || eveningParsed.kind === "invalid";
  const canSubmit =
    (morningChanged || eveningChanged) &&
    !invalidValues &&
    !morningMissingJustification &&
    !eveningMissingJustification &&
    !pending;

  const morningError =
    morningParsed.kind === "invalid"
      ? t("Saisis une température valide.")
      : morningMissingJustification
        ? t("Une justification est obligatoire pour modifier cette température.")
        : state.fieldErrors?.morning;
  const eveningError =
    eveningParsed.kind === "invalid"
      ? t("Saisis une température valide.")
      : eveningMissingJustification
        ? t("Une justification est obligatoire pour modifier cette température.")
        : state.fieldErrors?.evening;

  const title =
    action === "enter"
      ? t("Saisir les relevés")
      : action === "complete"
        ? t("Compléter les relevés")
        : t("Corriger les relevés");
  const triggerLabel =
    action === "enter" ? t("Saisir") : action === "complete" ? t("Compléter") : t("Corriger");
  const focusMorning = day.morning === null || day.evening !== null;
  const visibleGlobalError =
    state.status === "error" && state.message && !state.fieldErrors ? state.message : undefined;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        data-reading-action={action}
        data-equipment-id={equipment.id}
        data-reading-date={readingDate}
        className={
          action === "enter"
            ? "inline-flex items-center gap-1.5 rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-teal-700"
            : "inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
        }
      >
        {action === "enter" ? <PlusIcon className="size-4" /> : <PencilIcon className="size-4" />}
        {triggerLabel}
      </button>

      {open ? (
        <div
          role="presentation"
          onClick={() => setOpen(false)}
          data-reading-dialog-overlay
          className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/50 backdrop-blur-sm sm:items-center sm:p-8"
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="reading-form-title"
            data-reading-dialog-panel
            onClick={(event) => event.stopPropagation()}
            className="animate-fade-in max-h-[92dvh] w-full overflow-y-auto rounded-t-2xl border border-slate-200 bg-white shadow-xl sm:max-w-2xl sm:rounded-2xl"
          >
            <header className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-100 bg-white/95 px-5 py-4 backdrop-blur sm:px-6 sm:py-5">
              <div>
                <h2
                  id="reading-form-title"
                  className="text-lg font-semibold tracking-tight text-slate-900"
                >
                  {title}
                </h2>
                <p className="mt-0.5 text-sm text-slate-500">
                  {equipment.name} · <span className="capitalize">{formatDayLabel(locale, readingDate)}</span>
                </p>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label={t("Fermer")}
                className={ICON_BUTTON_CLASS}
              >
                <CloseIcon className="size-5" />
              </button>
            </header>

            <form
              action={formAction}
              data-reading-form
              onSubmit={(event) => {
                if (!canSubmit) {
                  event.preventDefault();
                }
              }}
              className="space-y-5 px-4 py-5 sm:px-6"
            >
              <input type="hidden" name="equipment_id" value={equipment.id} />
              <input type="hidden" name="reading_date" value={readingDate} />

              <div className="grid gap-3 sm:grid-cols-2">
                <SlotEditor
                  field="morning"
                  label={t("Matin (°C)")}
                  draft={morning}
                  effective={day.morning}
                  original={day.morning_original}
                  modified={day.morning_modified}
                  locale={locale}
                  error={morningError}
                  required={morningRequiresJustification}
                  autoFocus={focusMorning}
                  onChange={(value) => setMorning((current) => ({ ...current, value }))}
                  onJustificationChange={(justification) =>
                    setMorning((current) => ({ ...current, justification }))
                  }
                />
                <SlotEditor
                  field="evening"
                  label={t("Soir (°C)")}
                  draft={evening}
                  effective={day.evening}
                  original={day.evening_original}
                  modified={day.evening_modified}
                  locale={locale}
                  error={eveningError}
                  required={eveningRequiresJustification}
                  autoFocus={!focusMorning}
                  onChange={(value) => setEvening((current) => ({ ...current, value }))}
                  onJustificationChange={(justification) =>
                    setEvening((current) => ({ ...current, justification }))
                  }
                />
              </div>

              <p className="text-xs text-slate-500">
                {t("Plage cible : {min} à {max}. Laisse un champ vide pour ne pas le modifier.", {
                  min: formatTemperature(locale, equipment.min_temperature_celsius),
                  max: formatTemperature(locale, equipment.max_temperature_celsius),
                })}
              </p>

              {visibleGlobalError ? (
                <p
                  role="alert"
                  className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-sm text-rose-700"
                >
                  <AlertIcon className="mt-0.5 size-4 shrink-0" />
                  <span>{visibleGlobalError}</span>
                </p>
              ) : null}

              <div className="sticky bottom-0 -mx-4 flex justify-end gap-2 border-t border-slate-100 bg-white/95 px-4 py-4 backdrop-blur sm:-mx-6 sm:px-6">
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className={CANCEL_BUTTON_CLASS}
                >
                  {t("Annuler")}
                </button>
                <button type="submit" disabled={!canSubmit} className={SUBMIT_BUTTON_CLASS}>
                  {pending ? t("Enregistrement…") : t("Enregistrer")}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  );
}
