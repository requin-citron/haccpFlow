"use client";

import { PlusIcon, TrashIcon } from "@/components/icons";
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

export function validateProductRows(rows: ProductRowDraft[]): string | null {
  for (const [index, row] of rows.entries()) {
    if (!row.designation.trim()) {
      return `Ligne ${index + 1} : la désignation est obligatoire.`;
    }
    if (!/^\d+$/.test(row.pots.trim()) || Number(row.pots) > 1_000_000) {
      return `Ligne ${index + 1} : le nombre de pots doit être un entier positif.`;
    }
    const price = Number(row.prix.trim().replace(",", "."));
    if (!Number.isFinite(price) || price < 0) {
      return `Ligne ${index + 1} : le prix doit être un nombre positif.`;
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

function amount(row: ProductRowDraft): string {
  const value = Number.parseInt(row.pots, 10) * priceValue(row);
  return `€${(Number.isFinite(value) ? value : 0).toFixed(2).replace(".", ",")}`;
}

export function ProductRowsEditor({
  rows,
  onChange,
  disabled = false,
  label = "Lignes de produits",
}: {
  rows: ProductRowDraft[];
  onChange: (rows: ProductRowDraft[]) => void;
  disabled?: boolean;
  label?: string;
}) {
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
        <p className="text-sm font-medium text-slate-700">{label}</p>
        <span className="text-xs text-slate-500">
          {rows.length} ligne{rows.length === 1 ? "" : "s"}
        </span>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200">
        <table className="w-full min-w-[620px] text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-3 py-2 font-semibold">Désignation</th>
              <th className="w-24 px-3 py-2 font-semibold">Pots</th>
              <th className="w-32 px-3 py-2 font-semibold">Prix unitaire</th>
              <th className="w-28 px-3 py-2 text-right font-semibold">Montant</th>
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
                    aria-label={`Désignation ligne ${index + 1}`}
                    placeholder="BOCAL - ..."
                    className={CELL_INPUT}
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    value={row.pots}
                    onChange={(event) => update(index, "pots", event.target.value)}
                    disabled={disabled}
                    inputMode="numeric"
                    aria-label={`Nombre de pots ligne ${index + 1}`}
                    className={CELL_INPUT}
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    value={row.prix}
                    onChange={(event) => update(index, "prix", event.target.value)}
                    disabled={disabled}
                    inputMode="decimal"
                    aria-label={`Prix unitaire ligne ${index + 1}`}
                    placeholder="3,95"
                    className={CELL_INPUT}
                  />
                </td>
                <td className="whitespace-nowrap px-3 py-2 text-right font-medium text-slate-700">
                  {amount(row)}
                </td>
                <td className="px-2 py-2">
                  <button
                    type="button"
                    onClick={() => onChange(rows.filter((_, rowIndex) => rowIndex !== index))}
                    disabled={disabled}
                    aria-label={`Supprimer la ligne ${index + 1}`}
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
                  Totaux
                </td>
                <td className="px-3 py-2 font-semibold text-slate-900">{totalPots}</td>
                <td />
                <td className="px-3 py-2 text-right font-semibold text-slate-900">
                  €{totalAmount.toFixed(2).replace(".", ",")}
                </td>
                <td />
              </tr>
            </tfoot>
          ) : null}
        </table>
      </div>

      {rows.length === 0 ? (
        <p className="rounded-xl bg-slate-50 px-3 py-2 text-sm text-slate-500">
          Aucune ligne pour le moment.
        </p>
      ) : null}

      <button
        type="button"
        onClick={() =>
          onChange([...rows, { designation: "", pots: "0", prix: "0,00" }])
        }
        disabled={disabled || rows.length >= 100}
        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <PlusIcon className="size-4" />
        Ajouter une ligne
      </button>
    </div>
  );
}
