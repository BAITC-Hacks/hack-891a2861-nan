"use client";

import Link from "next/link";
import { useAuth } from "@/components/auth-provider";
import { useLocale } from "@/components/locale-provider";

export default function LandingPage() {
  const { locale } = useLocale();
  const { user } = useAuth();
  const destination = user?.role === "employee" && user.employee_id ? `/employee/${user.employee_id}` : "/hr";
  return <div className="landing">
    <section className="landing-hero shell">
      <div className="landing-copy"><span className="eyebrow">Halyk · HackAlem AI</span><h1>{locale === "ru" ? "Ваш рост больше не случаен" : "Your growth is no longer accidental"}</h1><p>{locale === "ru" ? "Career Quest превращает разрозненные HR-активности в понятную траекторию к следующему грейду." : "Career Quest turns scattered HR activities into a clear, evidence-backed path to your next grade."}</p><Link className="landing-cta" href={user ? destination : "/login"}>{user ? (locale === "ru" ? "Продолжить" : "Continue") : (locale === "ru" ? "Войти в Career Quest" : "Sign in to Career Quest")} <span>→</span></Link></div>
      <div className="career-visual"><div className="visual-card card-one"><small>01 · PROFILE</small><strong>Middle</strong><span>Current grade</span></div><div className="visual-line" /><div className="visual-card card-two"><small>AI NEXT STEP</small><strong>System Design</strong><span>Evidence-backed</span></div><div className="visual-line" /><div className="visual-card card-three"><small>TARGET</small><strong>Senior</strong><span>78% ready</span></div></div>
    </section>
    <section className="value-strip"><div className="shell value-grid"><div><strong>4</strong><span>{locale === "ru" ? "фактора в каждом решении" : "factors in every decision"}</span></div><div><strong>&lt; 2s</strong><span>{locale === "ru" ? "базовая рекомендация" : "baseline recommendation"}</span></div><div><strong>100%</strong><span>{locale === "ru" ? "проверяемые объяснения" : "traceable explanations"}</span></div></div></section>
  </div>;
}
