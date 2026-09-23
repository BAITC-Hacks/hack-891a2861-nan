"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import { useLocale } from "@/components/locale-provider";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const { locale } = useLocale();
  const [role, setRole] = useState<"employee" | "hr">("employee");
  const [username, setUsername] = useState("e0001");
  const [password, setPassword] = useState("employee-demo");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  function choose(next: "employee" | "hr") { setRole(next); setUsername(next === "hr" ? "hr" : "e0001"); setPassword(next === "hr" ? "hr-demo" : "employee-demo"); setError(""); }
  async function submit(event: FormEvent) { event.preventDefault(); setBusy(true); setError(""); try { const user = await login(username, password); router.push(user.role === "employee" && user.employee_id ? `/employee/${user.employee_id}` : "/hr"); } catch (reason) { setError(String(reason)); } finally { setBusy(false); } }
  return <div className="login-page"><div className="login-aside"><span className="eyebrow">CAREER QUEST</span><h1>{locale === "ru" ? "Развитие, которое видно" : "Development you can see"}</h1><p>{locale === "ru" ? "Персональная траектория для сотрудника. Целостная картина для HR." : "A personal trajectory for every employee. A coherent capability view for HR."}</p></div><form className="login-panel" onSubmit={submit}><span className="section-label">Secure workspace</span><h2>{locale === "ru" ? "Вход" : "Sign in"}</h2><div className="role-tabs"><button type="button" className={role === "employee" ? "active" : ""} onClick={() => choose("employee")}>{locale === "ru" ? "Сотрудник" : "Employee"}</button><button type="button" className={role === "hr" ? "active" : ""} onClick={() => choose("hr")}>HR</button></div><label><span>{locale === "ru" ? "Логин" : "Username"}</span><input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" /></label><label><span>{locale === "ru" ? "Пароль" : "Password"}</span><input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" /></label>{error && <div className="error-banner">{error}</div>}<button className="primary-button" disabled={busy}>{busy ? "..." : (locale === "ru" ? "Войти" : "Sign in")}</button><small className="demo-hint">{role === "employee" ? "Demo: e0001 / employee-demo" : "Demo: hr / hr-demo"}</small></form></div>;
}
