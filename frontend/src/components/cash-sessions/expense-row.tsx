import { DeleteExpenseButton } from "@/components/cash-sessions/delete-expense-button";
import { ExpenseFormDialog } from "@/components/cash-sessions/expense-form-dialog";
import { EXPENSE_KIND_LABELS, formatVatRate } from "@/lib/cash-session";
import { formatEuros } from "@/lib/format";
import type { CashExpense } from "@/lib/types";

export function ExpenseRow({
  sessionId,
  expense,
  isOpen,
}: {
  sessionId: string;
  expense: CashExpense;
  isOpen: boolean;
}) {
  const badge =
    expense.kind === "professional"
      ? "bg-sky-50 text-sky-700 ring-sky-200"
      : "bg-violet-50 text-violet-700 ring-violet-200";

  return (
    <li className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3">
      <div className="min-w-0">
        <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-slate-900">
          <span
            className={`rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset ${badge}`}
          >
            {EXPENSE_KIND_LABELS[expense.kind]}
          </span>
          <span className="truncate" title={expense.name}>
            {expense.name}
          </span>
        </p>
        <p className="mt-0.5 text-xs tabular-nums text-slate-500">
          {expense.quantity} × {formatEuros(expense.unit_price_cents)} · TVA{" "}
          {formatVatRate(expense.vat_rate)}
        </p>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold tabular-nums text-slate-900">
          {formatEuros(expense.total_cents)}
        </span>
        {isOpen ? (
          <>
            <ExpenseFormDialog sessionId={sessionId} expense={expense} />
            <DeleteExpenseButton
              sessionId={sessionId}
              expenseId={expense.id}
              name={expense.name}
            />
          </>
        ) : null}
      </div>
    </li>
  );
}
