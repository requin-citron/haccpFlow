"use client";

import { PlusIcon, TrashIcon } from "@/components/icons";
import { useI18n } from "@/components/locale-provider";
import { formatLocale, plural, t, type Locale } from "@/lib/i18n";
import type { ProductRow } from "@/lib/types";

export type ProductRowDraft = {
  designation: string;
  pots: string;
  prix: string;
};

const CELL_INPUT =
  "w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-teal-500 focus:ring-2 focus:ring-teal-500/15 disabled:bg-slate-50";

export function productRowsFromValue(value: ProductRow[] | string | null): ProductRowDraft[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((row) => ({
    designation: row.designation,
    pots: String(row.pots),
    prix: row.prix,
  }));
}

export function validateProductRows(locale: Locale, rows: ProductRowDraft[]): string | null {
  for (const [index, row] of rows.entries()) {
    if (!row.designation.trim()) {
      return t(locale, "Ligne {line} : la désignation est obligatoire.", {
        line: index + 1,
      });
    }
    if (!/^\d+$/.test(row.pots.trim()) || Number(row.pots) > 1_000_000) {
      return t(locale, "Ligne {line} : le nombre de pots doit être un entier positif.", {
        line: index + 1,
      });
    }
    const price = Number(row.prix.trim().replace(",", "."));
    if (!Number.isFinite(price) || price < 0) {
      return t(locale, "Ligne {line} : le prix doit être un nombre positif.", {
        line: index + 1,
      });
    }
  }
  return null;
}

export function productRowsToPayload(rows: ProductRowDraft[]): ProductRow[] {
  return rows.map((row) => ({
    designation: row.designation.trim(),
    pots: Number.parseInt(row.pots, 10),
    prix: row.prix.trim().replace(",", "."),
  }));
}

function priceValue(row: ProductRowDraft): number {
  const price = Number(row.prix.trim().replace(",", "."));
  return Number.isFinite(price) ? price : 0;
}

function amount(locale: Locale, row: ProductRowDraft): string {
  const value = Number.parseInt(row.pots, 10) * priceValue(row);
  return new Intl.NumberFormat(formatLocale(locale), {
    style: "currency",
    currency: "EUR",
  }).format(Number.isFinite(value) ? value : 0);
}

export function ProductRowsEditor({
  rows,
  onChange,
  disabled = false,
  label,
}: {
  rows: ProductRowDraft[];
  onChange: (rows: ProductRowDraft[]) => void;
  disabled?: boolean;
  label?: string;
}) {
  const { locale, t: translate } = useI18n();
  function update(index: number, key: keyof ProductRowDraft, value: string): void {
    onChange(
      rows.map((row, rowIndex) =>
        rowIndex === index ? { ...row, [key]: value } : row,
      ),
    );
  }

  const totalPots = rows.reduce(
    (total, row) => total + (Number.parseInt(row.pots, 10) || 0),
    0,
  );
  const totalAmount = rows.reduce(
    (total, row) => total + (Number.parseInt(row.pots, 10) || 0) * priceValue(row),
    0,
  );

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-700">
          {label ?? translate("Lignes de produits")}
        </p>
        <span className="text-xs text-slate-500">
          {plural(
            locale,
            { one: "{count} ligne", other: "{count} lignes" },
            rows.length,
          )}
        </span>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200">
        <table className="w-full min-w-[620px] text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-3 py-2 font-semibold">{translate("Désignation")}</th>
              <th className="w-24 px-3 py-2 font-semibold">{translate("Pots")}</th>
              <th className="w-32 px-3 py-2 font-semibold">{translate("Prix unitaire")}</th>
              <th className="w-28 px-3 py-2 text-right font-semibold">{translate("Montant")}</th>
              <th className="w-10 px-2 py-2" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row, index) => (
              <tr key={index}>
                <td className="px-3 py-2">
                  <input
                    value={row.designation}
                    onChange={(event) => update(index, "designation", event.target.value)}
                    disabled={disabled}
                    aria-label={translate("Désignation ligne {line}", { line: index + 1 })}
                    placeholder={translate("BOCAL - ...")}
                    className={CELL_INPUT}
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    value={row.pots}
                    onChange={(event) => update(index, "pots", event.target.value)}
                    disabled={disabled}
                    inputMode="numeric"
                    aria-label={translate("Nombre de pots ligne {line}", { line: index + 1 })}
                    className={CELL_INPUT}
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    value={row.prix}
                    onChange={(event) => update(index, "prix", event.target.value)}
                    disabled={disabled}
                    inputMode="decimal"
                    aria-label={translate("Prix unitaire ligne {line}", { line: index + 1 })}
                    placeholder={locale === "en" ? "3.95" : "3,95"}
                    className={CELL_INPUT}
                  />
                </td>
                <td className="whitespace-nowrap px-3 py-2 text-right font-medium text-slate-700">
                  {amount(locale, row)}
                </td>
                <td className="px-2 py-2">
                  <button
                    type="button"
                    onClick={() => onChange(rows.filter((_, rowIndex) => rowIndex !== index))}
                    disabled={disabled}
                    aria-label={translate("Supprimer la ligne {line}", { line: index + 1 })}
                    className="rounded-lg p-1.5 text-slate-400 transition hover:bg-rose-50 hover:text-rose-600 disabled:opacity-50"
                  >
                    <TrashIcon className="size-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
          {rows.length > 0 ? (
            <tfoot className="bg-slate-50/70 text-sm">
              <tr>
                <td className="px-3 py-2 text-right font-medium text-slate-600" colSpan={1}>
                  {translate("Totaux")}
                </td>
                <td className="px-3 py-2 font-semibold text-slate-900">{totalPots}</td>
                <td />
                <td className="px-3 py-2 text-right font-semibold text-slate-900">
                  {new Intl.NumberFormat(formatLocale(locale), {
                    style: "currency",
                    currency: "EUR",
                  }).format(totalAmount)}
                </td>
                <td />
              </tr>
            </tfoot>
          ) : null}
        </table>
      </div>

      {rows.length === 0 ? (
        <p className="rounded-xl bg-slate-50 px-3 py-2 text-sm text-slate-500">
          {translate("Aucune ligne pour le moment.")}
        </p>
      ) : null}

      <button
        type="button"
        onClick={() =>
          onChange([
            ...rows,
            { designation: "", pots: "0", prix: locale === "en" ? "0.00" : "0,00" },
          ])
        }
        disabled={disabled || rows.length >= 100}
        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <PlusIcon className="size-4" />
        {translate("Ajouter une ligne")}
      </button>
    </div>
  );
}
