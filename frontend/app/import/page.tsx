"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import { useLocale } from "@/components/locale-provider";
import { api } from "@/lib/api";

const fields = [
  ["employees", "employees.json", ".json"],
  ["skills", "skills.json", ".json"],
  ["events", "events.json", ".json"],
  ["history", "activity_history.csv", ".csv"],
] as const;

export default function ImportPage() {
  const { locale, t } = useLocale();
  const { user, loading } = useAuth();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    if (loading) return;
    if (!user) router.replace("/login");
    else if (user.role === "employee" && user.employee_id) router.replace(`/employee/${user.employee_id}`);
  }, [loading, router, user]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    try { const result = await api.importDataset(new FormData(event.currentTarget)); setMessage(`${t.imported}: ${Object.entries(result.counts).map(([key,value]) => `${key} ${value}`).join(", ")}`); }
    catch (reason) { setError(String(reason)); } finally { setBusy(false); }
  }
  return <div className="page narrow-shell"><section className="page-heading"><div><span className="eyebrow">Validated import</span><h1>{t.importTitle}</h1><p>{t.importHelp}</p></div></section><form className="import-panel" onSubmit={submit}>{fields.map(([name,label,accept]) => <label className="file-field" key={name}><span><strong>{label}</strong><small>{locale === "ru" ? "Выберите файл" : "Choose a file"}</small></span><input required type="file" name={name} accept={accept} /></label>)}<div className="security-note"><strong>{locale === "ru" ? "Атомарная загрузка" : "Atomic import"}</strong><p>{locale === "ru" ? "Схемы, ссылки и диапазоны проверяются до записи." : "Schemas, references and ranges are validated before any data is committed."}</p></div>{error && <div className="error-banner">{error}</div>}{message && <div className="success-banner">{message}</div>}<button className="primary-button" disabled={busy}>{busy ? t.loading : t.upload}</button></form></div>;
}
