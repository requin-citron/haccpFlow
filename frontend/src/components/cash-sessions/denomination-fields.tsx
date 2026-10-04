import { COIN_DENOMINATIONS, NOTE_DENOMINATIONS, type Denomination } from "@/lib/cash-register";
import type { CountsDraft } from "@/lib/cash-session";
import { LABEL_CLASS } from "@/lib/ui";

function CountField({
  denomination,
  value,
  idPrefix,
  onChange,
}: {
  denomination: Denomination;
  value: string;
  idPrefix: string;
  onChange: (field: string, value: string) => void;
}) {
  const id = `${idPrefix}${denomination.field}`;

  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-[11px] font-medium text-slate-600">
        {denomination.label}
      </label>
      <input
        id={id}
        name={denomination.field}
        type="number"
        min={0}
        step={1}
        inputMode="numeric"
        value={value}
        placeholder="0"
        onChange={(event) => onChange(denomination.field, event.target.value)}
        className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-sm tabular-nums text-slate-900 shadow-sm outline-none transition placeholder:text-slate-300 focus:border-teal-500 focus:ring-4 focus:ring-teal-500/15"
      />
    </div>
  );
}

/** The twelve counters, laid out like the cash register form. */
export function DenominationFields({
  draft,
  onChange,
  idPrefix = "",
}: {
  draft: CountsDraft;
  onChange: (field: string, value: string) => void;
  idPrefix?: string;
}) {
  return (
    <>
      <fieldset className="space-y-2">
        <legend className={LABEL_CLASS}>Pièces</legend>
        <div className="grid grid-cols-4 gap-3">
          {COIN_DENOMINATIONS.map((denomination) => (
            <CountField
              key={denomination.field}
              denomination={denomination}
              value={draft[denomination.field] ?? ""}
              idPrefix={idPrefix}
              onChange={onChange}
            />
          ))}
        </div>
      </fieldset>

      <fieldset className="space-y-2">
        <legend className={LABEL_CLASS}>Billets</legend>
        <div className="grid grid-cols-4 gap-3">
          {NOTE_DENOMINATIONS.map((denomination) => (
            <CountField
              key={denomination.field}
              denomination={denomination}
              value={draft[denomination.field] ?? ""}
              idPrefix={idPrefix}
              onChange={onChange}
            />
          ))}
        </div>
      </fieldset>
    </>
  );
}
