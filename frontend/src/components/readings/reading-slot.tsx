import { formatTemperature, readingSourceLabel } from "@/lib/format";
import { t, type Locale } from "@/lib/i18n";
import type {
  TemperatureReadingCorrection,
  TemperatureReadingSlot,
} from "@/lib/types";

function CorrectionDetails({
  effective,
  original,
  modified,
  locale,
}: {
  effective: TemperatureReadingSlot;
  original: TemperatureReadingSlot | null;
  modified: TemperatureReadingCorrection;
  locale: Locale;
}) {
  const originalValue = original?.temperature_celsius ?? modified.previous_celsius;
  return (
    <details
      data-correction-details
      className="mt-2 border-t border-slate-200/70 pt-2"
    >
      <summary className="cursor-pointer select-none text-xs font-semibold text-teal-700 marker:text-teal-600">
        {t(locale, "Détail de la correction")}
      </summary>
      <dl className="mt-2 space-y-1.5 text-xs">
        <div className="flex items-start justify-between gap-3">
          <dt className="text-slate-500">{t(locale, "Mesure originale")}</dt>
          <dd className="text-right font-medium tabular-nums text-slate-700">
            {formatTemperature(locale, originalValue)}
          </dd>
        </div>
        <div className="flex items-start justify-between gap-3">
          <dt className="text-slate-500">{t(locale, "Valeur corrigée")}</dt>
          <dd className="text-right font-medium tabular-nums text-slate-700">
            {formatTemperature(locale, effective.temperature_celsius)}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">{t(locale, "Justification")}</dt>
          <dd className="mt-0.5 whitespace-pre-wrap break-words text-slate-700">
            {modified.justification}
          </dd>
        </div>
      </dl>
    </details>
  );
}

export function ReadingSlotDisplay({
  label,
  effective,
  original,
  modified,
  locale,
  compact = false,
}: {
  label: string;
  effective: TemperatureReadingSlot | null;
  original: TemperatureReadingSlot | null;
  modified: TemperatureReadingCorrection | null;
  locale: Locale;
  compact?: boolean;
}) {
  if (effective === null) {
    if (compact) {
      return <span className="text-slate-400">—</span>;
    }
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/70 px-4 py-3">
        <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">{label}</p>
        <p className="mt-1 text-sm text-slate-400">{t(locale, "Non saisi")}</p>
      </div>
    );
  }

  const tone = effective.is_compliant
    ? { box: "border-emerald-200 bg-emerald-50", value: "text-emerald-700" }
    : { box: "border-rose-200 bg-rose-50", value: "text-rose-700" };

  if (compact) {
    return (
      <div>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className={`font-medium tabular-nums ${tone.value}`}>
            {formatTemperature(locale, effective.temperature_celsius)}
          </span>
          {modified ? (
            <span
              data-reading-corrected
              className="rounded-full bg-amber-50 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700 ring-1 ring-inset ring-amber-200"
            >
              {t(locale, "Corrigé")}
            </span>
          ) : null}
        </div>
        {modified ? (
          <CorrectionDetails
            effective={effective}
            original={original}
            modified={modified}
            locale={locale}
          />
        ) : null}
      </div>
    );
  }

  return (
    <div className={`rounded-xl border px-4 py-3 ${tone.box}`}>
      <div className="flex items-start justify-between gap-2">
        <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{label}</p>
        {modified ? (
          <span
            data-reading-corrected
            className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-700 ring-1 ring-inset ring-amber-200"
          >
            {t(locale, "Corrigé")}
          </span>
        ) : null}
      </div>
      <p className={`mt-1 text-lg font-semibold tabular-nums ${tone.value}`}>
        {formatTemperature(locale, effective.temperature_celsius)}
      </p>
      <p className="mt-0.5 text-xs text-slate-500">
        {readingSourceLabel(locale, effective.source)} ·{" "}
        {effective.is_compliant ? t(locale, "conforme") : t(locale, "hors seuils")}
      </p>
      {modified ? (
        <CorrectionDetails
          effective={effective}
          original={original}
          modified={modified}
          locale={locale}
        />
      ) : null}
    </div>
  );
}
