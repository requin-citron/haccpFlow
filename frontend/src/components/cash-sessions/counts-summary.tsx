import { DENOMINATIONS } from "@/lib/cash-register";
import { formatEuros } from "@/lib/format";
import type { CashRegisterCounts } from "@/lib/types";

/** A read-only count: the twelve denominations plus their total. */
export function CountsSummary({
  counts,
  totalCents,
  label,
}: {
  counts: CashRegisterCounts;
  totalCents: number;
  label: string;
}) {
  return (
    <div className="rounded-xl bg-slate-50 px-4 py-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{label}</p>
        <p className="text-lg font-semibold tabular-nums text-slate-900">
          {formatEuros(totalCents)}
        </p>
      </div>
      <ul className="mt-2 grid grid-cols-4 gap-1.5">
        {DENOMINATIONS.map((denomination) => {
          const count = counts[denomination.field];
          return (
            <li
              key={denomination.field}
              className={`rounded-lg px-2 py-1.5 text-center ${
                count > 0 ? "bg-white text-slate-700" : "text-slate-300"
              }`}
            >
              <span className="block text-[11px] font-semibold tabular-nums">{count}</span>
              <span className="block text-[11px]">{denomination.label}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
