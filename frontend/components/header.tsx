"use client";

import Link from "next/link";
import { useLocale } from "./locale-provider";

export function Header() {
  const { locale, setLocale, t } = useLocale();
  return (
    <header className="header">
      <Link href="/" className="brand" aria-label="Career Quest home">
        <span className="brand-mark">CQ</span>
        <span><strong>{t.product}</strong><small>{t.subtitle}</small></span>
      </Link>
      <nav>
        <Link href="/">{t.employee}</Link>
        <Link href="/hr">{t.hr}</Link>
        <Link href="/import">{t.import}</Link>
      </nav>
      <div className="locale-switch" aria-label="Language selector">
        <button className={locale === "ru" ? "active" : ""} onClick={() => setLocale("ru")}>RU</button>
        <button className={locale === "en" ? "active" : ""} onClick={() => setLocale("en")}>EN</button>
      </div>
    </header>
  );
}
