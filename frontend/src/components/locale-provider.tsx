"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import {
  DEFAULT_LOCALE,
  LOCALE_COOKIE,
  LOCALE_MAX_AGE_SECONDS,
  LOCALE_STORAGE_KEY,
  normalizeLocale,
  t,
  type Locale,
  type TranslationVariables,
} from "@/lib/i18n";

type LocaleContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: Parameters<typeof t>[1], variables?: TranslationVariables) => string;
};

const LocaleContext = createContext<LocaleContextValue | null>(null);

function readStoredLocale(): Locale | null {
  try {
    const value = window.localStorage.getItem(LOCALE_STORAGE_KEY);
    return value === "fr" || value === "en" ? normalizeLocale(value) : null;
  } catch {
    return null;
  }
}

function writeLocale(locale: Locale): void {
  try {
    window.localStorage.setItem(LOCALE_STORAGE_KEY, locale);
  } catch {
    // The cookie still carries the choice for this browser.
  }
  document.cookie = `${LOCALE_COOKIE}=${locale}; path=/; max-age=${LOCALE_MAX_AGE_SECONDS}; SameSite=Lax`;
  document.documentElement.lang = locale;
}

export function LocaleProvider({
  initialLocale,
  children,
}: {
  initialLocale: Locale;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [locale, setLocaleState] = useState<Locale>(initialLocale);

  useEffect(() => {
    const stored = readStoredLocale();
    if (stored && stored !== initialLocale) {
      writeLocale(stored);
      setLocaleState(stored);
      router.refresh();
      return;
    }
    if (!stored) {
      writeLocale(initialLocale);
    }
  }, [initialLocale, router]);

  const value = useMemo<LocaleContextValue>(
    () => ({
      locale,
      setLocale: (nextLocale) => {
        writeLocale(nextLocale);
        setLocaleState(nextLocale);
        router.refresh();
      },
      t: (key, variables) => t(locale, key, variables),
    }),
    [locale, router],
  );

  return (
    <LocaleContext.Provider value={value}>
      {children}
    </LocaleContext.Provider>
  );
}

export function useI18n(): LocaleContextValue {
  const value = useContext(LocaleContext);
  if (!value) {
    return {
      locale: DEFAULT_LOCALE,
      setLocale: () => undefined,
      t: (key, variables) => t(DEFAULT_LOCALE, key, variables),
    };
  }
  return value;
}
