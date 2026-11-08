"use client";

import { useI18n } from "@/components/locale-provider";

export function LocaleSwitcher({ compact = false }: { compact?: boolean }) {
  const { locale, setLocale, t } = useI18n();
  const next = locale === "fr" ? "en" : "fr";

  return (
    <button
      type="button"
      onClick={() => setLocale(next)}
      aria-label={t("Changer la langue")}
      title={t("Changer la langue")}
      className={
        compact
          ? "rounded-lg px-2 py-1 text-xs font-semibold tracking-wide text-slate-300 ring-1 ring-inset ring-slate-700 transition hover:bg-slate-800 hover:text-white"
          : "rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-semibold tracking-wide text-slate-600 transition hover:bg-slate-50"
      }
    >
      {t("FR / EN")}
    </button>
  );
}
