"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { copy } from "@/lib/i18n";
import type { Locale } from "@/lib/types";

interface LocaleContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (typeof copy)["en"];
}

const LocaleContext = createContext<LocaleContextValue | null>(null);

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("ru");

  useEffect(() => {
    const stored = window.localStorage.getItem("career-quest-locale");
    // Locale is a browser preference and is intentionally restored after hydration.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (stored === "en" || stored === "ru") setLocaleState(stored);
  }, []);

  const value = useMemo(
    () => ({
      locale,
      setLocale: (next: Locale) => {
        setLocaleState(next);
        window.localStorage.setItem("career-quest-locale", next);
      },
      t: copy[locale],
    }),
    [locale],
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  const value = useContext(LocaleContext);
  if (!value) throw new Error("useLocale must be used within LocaleProvider");
  return value;
}
