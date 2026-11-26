"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState, useTransition } from "react";

import {
  AlertIcon,
  CalendarIcon,
  CheckIcon,
  CloseIcon,
} from "@/components/icons";
import { useI18n } from "@/components/locale-provider";
import {
  DASHBOARD_PRESETS,
  dashboardPresetRange,
  dashboardRangeLabel,
  sameDashboardRange,
  type DashboardRange,
} from "@/lib/dashboard";
import { addDays, daysBetween, formatDayLabel, isIsoDate } from "@/lib/format";
import { FIELD_CLASS, ICON_BUTTON_CLASS } from "@/lib/ui";

function rangeUrl(range: DashboardRange): string {
  const query = new URLSearchParams({ from: range.from, to: range.to });
  return `/?${query.toString()}`;
}

export function DashboardTimeRangePicker({
  range,
  today,
}: {
  range: DashboardRange;
  today: string;
}) {
  const { locale, t } = useI18n();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [fromDraft, setFromDraft] = useState(range.from);
  const [toDraft, setToDraft] = useState(range.to);
  const [error, setError] = useState("");
  const [pending, startTransition] = useTransition();
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  const presetRanges = useMemo(
    () =>
      DASHBOARD_PRESETS.map((preset) => ({
        ...preset,
        range: dashboardPresetRange(preset.value, today),
      })),
    [today],
  );
  const summaryLabel =
    range.from === today && range.to === today
      ? t("Aujourd'hui")
      : range.from === addDays(today, -1) && range.to === addDays(today, -1)
        ? t("Hier")
        : dashboardRangeLabel(locale, range);

  useEffect(() => {
    if (!open) {
      return;
    }

    const onPointerDown = (event: PointerEvent) => {
      if (
        containerRef.current &&
        event.target instanceof Node &&
        !containerRef.current.contains(event.target)
      ) {
        setOpen(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const navigateTo = (next: DashboardRange) => {
    setOpen(false);
    setError("");
    startTransition(() => {
      router.push(rangeUrl(next));
    });
  };

  const applyCustomRange = () => {
    if (!isIsoDate(fromDraft) || !isIsoDate(toDraft)) {
      setError(t("Les deux dates sont obligatoires."));
      return;
    }
    if (daysBetween(fromDraft, toDraft) < 0) {
      setError(t("La date de début doit précéder la date de fin."));
      return;
    }
    navigateTo({ from: fromDraft, to: toDraft });
  };

  return (
    <div ref={containerRef} className="relative shrink-0">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => {
          setFromDraft(range.from);
          setToDraft(range.to);
          setError("");
          setOpen((current) => !current);
        }}
        aria-haspopup="dialog"
        aria-expanded={open}
        className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:border-slate-400 hover:bg-slate-50 focus:outline-none focus-visible:ring-4 focus-visible:ring-teal-500/20"
      >
        <CalendarIcon className="size-4 text-slate-500" />
        <span className="max-w-[15rem] truncate">{summaryLabel}</span>
      </button>

      {open ? (
        <div
          role="dialog"
          aria-label={t("Choisir une période")}
          className="absolute right-0 z-40 mt-2 w-[min(92vw,38rem)] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl"
        >
          <header className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <div>
              <p className="text-sm font-semibold text-slate-900">{t("Période")}</p>
              <p className="mt-0.5 text-xs text-slate-500">
                {t("Choisis un raccourci ou une plage personnalisée.")}
              </p>
            </div>
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                triggerRef.current?.focus();
              }}
              aria-label={t("Fermer")}
              className={ICON_BUTTON_CLASS}
            >
              <CloseIcon className="size-4" />
            </button>
          </header>

          <div className="grid gap-4 p-4 sm:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
            <div className="space-y-1">
              {presetRanges.map((preset) => {
                const selected = sameDashboardRange(preset.range, range);
                return (
                  <button
                    key={preset.value}
                    type="button"
                    disabled={pending}
                    onClick={() => navigateTo(preset.range)}
                    className={`flex min-h-10 w-full items-center justify-between rounded-lg px-3 text-left text-sm transition ${
                      selected
                        ? "bg-teal-50 font-medium text-teal-800"
                        : "text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    <span>{t(preset.labelKey)}</span>
                    {selected ? <CheckIcon className="size-4" /> : null}
                  </button>
                );
              })}
            </div>

            <div className="space-y-3 rounded-xl bg-slate-50 p-3.5">
              <div>
                <p className="text-sm font-semibold text-slate-800">
                  {t("Plage personnalisée")}
                </p>
                <p className="mt-0.5 text-xs text-slate-500">
                  {t("Les dates sont interprétées en UTC.")}
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <label className="space-y-1 text-xs font-medium text-slate-600">
                  <span>{t("Du")}</span>
                  <input
                    type="date"
                    value={fromDraft}
                    max={toDraft}
                    onChange={(event) => {
                      setFromDraft(event.target.value);
                      setError("");
                    }}
                    className={FIELD_CLASS}
                  />
                </label>
                <label className="space-y-1 text-xs font-medium text-slate-600">
                  <span>{t("Au")}</span>
                  <input
                    type="date"
                    value={toDraft}
                    min={fromDraft}
                    onChange={(event) => {
                      setToDraft(event.target.value);
                      setError("");
                    }}
                    className={FIELD_CLASS}
                  />
                </label>
              </div>

              {error ? (
                <p
                  role="alert"
                  className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700"
                >
                  <AlertIcon className="mt-0.5 size-3.5 shrink-0" />
                  <span>{error}</span>
                </p>
              ) : null}

              <button
                type="button"
                onClick={applyCustomRange}
                disabled={pending}
                className="inline-flex min-h-10 w-full items-center justify-center rounded-lg bg-teal-600 px-3 text-sm font-semibold text-white transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {t("Appliquer la période")}
              </button>

              <p className="text-[11px] text-slate-500">
                {t("Plage active : du {from} au {to}.", {
                  from: formatDayLabel(locale, range.from),
                  to: formatDayLabel(locale, range.to),
                })}
              </p>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
