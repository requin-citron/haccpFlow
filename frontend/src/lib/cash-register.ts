import type { CashRegister, CashRegisterCounts } from "@/lib/types";

export type DenominationField = keyof CashRegisterCounts;

export type Denomination = {
  field: DenominationField;
  label: string;
  cents: number;
  kind: "coin" | "note";
};

/** The twelve counted denominations, in the order they are presented. */
export const DENOMINATIONS: Denomination[] = [
  { field: "coins_1_cent", label: "1 c", cents: 1, kind: "coin" },
  { field: "coins_2_cent", label: "2 c", cents: 2, kind: "coin" },
  { field: "coins_5_cent", label: "5 c", cents: 5, kind: "coin" },
  { field: "coins_10_cent", label: "10 c", cents: 10, kind: "coin" },
  { field: "coins_20_cent", label: "20 c", cents: 20, kind: "coin" },
  { field: "coins_50_cent", label: "50 c", cents: 50, kind: "coin" },
  { field: "coins_1_euro", label: "1 €", cents: 100, kind: "coin" },
  { field: "coins_2_euro", label: "2 €", cents: 200, kind: "coin" },
  { field: "notes_5_euro", label: "5 €", cents: 500, kind: "note" },
  { field: "notes_10_euro", label: "10 €", cents: 1000, kind: "note" },
  { field: "notes_20_euro", label: "20 €", cents: 2000, kind: "note" },
  { field: "notes_50_euro", label: "50 €", cents: 5000, kind: "note" },
];

export const COIN_DENOMINATIONS = DENOMINATIONS.filter(
  (denomination) => denomination.kind === "coin",
);
export const NOTE_DENOMINATIONS = DENOMINATIONS.filter(
  (denomination) => denomination.kind === "note",
);

export function emptyCounts(): CashRegisterCounts {
  return Object.fromEntries(
    DENOMINATIONS.map((denomination) => [denomination.field, 0]),
  ) as CashRegisterCounts;
}

export function countsOf(cashRegister: CashRegister): CashRegisterCounts {
  return Object.fromEntries(
    DENOMINATIONS.map((denomination) => [
      denomination.field,
      cashRegister[denomination.field],
    ]),
  ) as CashRegisterCounts;
}

export function totalCents(counts: CashRegisterCounts): number {
  return DENOMINATIONS.reduce(
    (total, denomination) => total + counts[denomination.field] * denomination.cents,
    0,
  );
}
