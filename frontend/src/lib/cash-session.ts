import { DENOMINATIONS, emptyCounts } from "@/lib/cash-register";
import type { CashExpenseKind, CashRegisterCounts } from "@/lib/types";

export const EXPENSE_KIND_LABELS: Record<CashExpenseKind, string> = {
  professional: "Frais pro",
  personal: "Frais perso",
};

export const EXPENSE_KIND_HINTS: Record<CashExpenseKind, string> = {
  professional: "Achat ou dépense pour l'activité, payé avec la caisse.",
  personal: "Prélèvement pour le gérant, sorti de la caisse.",
};

/** A count being edited: a zero stays an empty field, like the register form. */
export type CountsDraft = Record<string, string>;

export function countsDraft(counts?: CashRegisterCounts | null): CountsDraft {
  const source = counts ?? emptyCounts();
  return Object.fromEntries(
    DENOMINATIONS.map((denomination) => {
      const value = source[denomination.field];
      return [denomination.field, value > 0 ? String(value) : ""];
    }),
  );
}

function draftCount(draft: CountsDraft, field: string): number {
  const value = Number(draft[field] ?? "");
  return Number.isFinite(value) && value > 0 ? Math.floor(value) : 0;
}

export function draftTotals(draft: CountsDraft): CashRegisterCounts {
  return Object.fromEntries(
    DENOMINATIONS.map((denomination) => [
      denomination.field,
      draftCount(draft, denomination.field),
    ]),
  ) as CashRegisterCounts;
}

export function draftTotalCents(draft: CountsDraft): number {
  return DENOMINATIONS.reduce(
    (total, denomination) =>
      total + draftCount(draft, denomination.field) * denomination.cents,
    0,
  );
}

/** "12,50" or "12.5" into cents; null when the input is not a valid amount. */
export function eurosToCents(value: string): number | null {
  const normalized = value.trim().replace(",", ".");
  if (!/^\d+(\.\d{1,2})?$/.test(normalized)) {
    return null;
  }
  const [whole, decimals = ""] = normalized.split(".");
  return Number(whole) * 100 + Number(decimals.padEnd(2, "0"));
}

/** Cents into what a number input expects, e.g. 1250 -> "12.50". */
export function centsToEurosInput(cents: number): string {
  return (cents / 100).toFixed(2);
}

/** "20" or "20,5" into the decimal string the API stores; null when invalid. */
export function normalizeVatRate(value: string): string | null {
  const trimmed = value.trim();
  if (trimmed === "") {
    return "0.00";
  }
  const normalized = trimmed.replace(",", ".");
  if (!/^\d+(\.\d{1,2})?$/.test(normalized)) {
    return null;
  }
  const rate = Number(normalized);
  if (rate > 100) {
    return null;
  }
  return rate.toFixed(2);
}

export function formatVatRate(value: string): string {
  const rate = Number(value);
  if (!Number.isFinite(rate)) {
    return `${value} %`;
  }
  const rounded = Math.round(rate * 100) / 100;
  return `${Number.isInteger(rounded) ? rounded : rounded.toFixed(2)} %`;
}

export function expenseTotalCents(quantity: number, unitPriceCents: number): number {
  return quantity * unitPriceCents;
}
