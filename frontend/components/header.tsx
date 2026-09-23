"use client";

import Link from "next/link";
import { useLocale } from "./locale-provider";
import { useAuth } from "./auth-provider";

export function Header() {
  const { locale, setLocale, t } = useLocale();
  const { user, logout } = useAuth();
  return (
    <header className="header">
      <Link href="/" className="brand" aria-label="Career Quest home">
        <span className="brand-mark">CQ</span>
        <span><strong>{t.product}</strong><small>{t.subtitle}</small></span>
      </Link>
      <nav>
        <Link href="/">Home</Link>
        {user?.role === "employee" && user.employee_id && <Link href={`/employee/${user.employee_id}`}>{t.employee}</Link>}
        {(user?.role === "hr" || user?.role === "admin") && <Link href="/hr">{t.hr}</Link>}
        {(user?.role === "hr" || user?.role === "admin") && <Link href="/import">{t.import}</Link>}
      </nav>
      {user ? <button className="text-button" onClick={logout}>{user.display_name} · Logout</button> : <Link className="login-link" href="/login">Login</Link>}
      <div className="locale-switch" aria-label="Language selector">
        <button className={locale === "ru" ? "active" : ""} onClick={() => setLocale("ru")}>RU</button>
        <button className={locale === "en" ? "active" : ""} onClick={() => setLocale("en")}>EN</button>
      </div>
    </header>
  );
}
