import { BanknoteIcon } from "@/components/icons";
import { CashRegisterFormDialog } from "@/components/cash-registers/cash-register-form-dialog";
import { DeleteCashRegisterButton } from "@/components/cash-registers/delete-cash-register-button";
import { DENOMINATIONS, countsOf } from "@/lib/cash-register";
import { formatDate, formatEuros } from "@/lib/format";
import type { CashRegister } from "@/lib/types";

export function CashRegisterCard({
  cashRegister,
  isAdmin,
}: {
  cashRegister: CashRegister;
  isAdmin: boolean;
}) {
  const counts = countsOf(cashRegister);

  return (
    <article className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300 hover:shadow-md">
      <header className="flex items-start gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-emerald-50 text-emerald-600 ring-1 ring-emerald-100">
          <BanknoteIcon className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="truncate font-semibold text-slate-900" title={cashRegister.name}>
            {cashRegister.name}
          </h3>
          <span className="mt-1 inline-flex rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-200">
            Caisse
          </span>
        </div>
      </header>

      <div className="rounded-xl bg-slate-50 px-4 py-3">
        <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
          Comptage initial
        </p>
        <p className="mt-0.5 text-lg font-semibold tabular-nums text-slate-900">
          {formatEuros(cashRegister.total_cents)}
        </p>
      </div>

      <ul className="grid grid-cols-4 gap-1.5">
        {DENOMINATIONS.map((denomination) => {
          const count = counts[denomination.field];
          return (
            <li
              key={denomination.field}
              className={`rounded-lg px-2 py-1.5 text-center ${
                count > 0 ? "bg-slate-50 text-slate-700" : "text-slate-300"
              }`}
            >
              <span className="block text-[11px] font-semibold tabular-nums">{count}</span>
              <span className="block text-[11px]">{denomination.label}</span>
            </li>
          );
        })}
      </ul>

      <p className="mt-auto text-xs text-slate-400">
        Enregistrée le {formatDate(cashRegister.created_at)}
      </p>

      <footer className="flex items-center justify-between gap-2 border-t border-slate-100 pt-4">
        <CashRegisterFormDialog cashRegister={cashRegister} />
        {isAdmin ? <DeleteCashRegisterButton id={cashRegister.id} label={cashRegister.name} /> : null}
      </footer>
    </article>
  );
}
