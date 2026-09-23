"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import { useLocale } from "@/components/locale-provider";
import { api } from "@/lib/api";
import type { HRDashboard } from "@/lib/types";

export default function HRPage() {
  const { locale, t } = useLocale();
  const { user, loading } = useAuth();
  const router = useRouter();
  const [data, setData] = useState<HRDashboard | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (loading) return;
    if (!user) { router.replace("/login"); return; }
    if (user.role === "employee") { if (user.employee_id) router.replace(`/employee/${user.employee_id}`); return; }
    api.dashboard(locale).then(setData).catch((reason) => setError(String(reason)));
  }, [loading, locale, router, user]);
  if (!data) return <div className="page shell"><p>{error || t.loading}</p></div>;
  const maxGap = Math.max(...data.top_skill_gaps.map((item) => item.employees), 1);
  return <div className="page shell">
    <section className="page-heading"><div><span className="eyebrow">People analytics</span><h1>{t.hr}</h1><p>{locale === "ru" ? "Агрегированный обзор развития без публичных рейтингов" : "Aggregated development insights without public employee rankings"}</p></div><Link className="secondary-button" href="/import">{t.import}</Link></section>
    <section className="metric-grid"><div className="metric"><span>{t.employees}</span><strong>{data.summary.employees}</strong><small>active profiles</small></div><div className="metric accent"><span>{t.completionRate}</span><strong>{data.summary.completion_rate}%</strong><small>all activities</small></div><div className="metric warn"><span>{t.withoutStep}</span><strong>{data.summary.employees_without_step}</strong><small>requires catalogue review</small></div></section>
    <div className="dashboard-grid">
      <section className="panel"><span className="section-label">Capability map</span><h2>{t.skillGaps}</h2><div className="bar-chart">{data.top_skill_gaps.map((item) => <div key={item.skill_code}><div><span>{item.skill_name}</span><strong>{item.employees}</strong></div><div className="bar-track"><i style={{ width: `${item.employees / maxGap * 100}%` }} /></div></div>)}</div></section>
      <section className="panel"><span className="section-label">Coverage</span><h2>{t.withoutStep}</h2>{data.employees_without_step.length ? <div className="people-list">{data.employees_without_step.map((employee) => <Link href={`/employee/${employee.employee_id}`} key={employee.employee_id}><span>{employee.display_name}</span><small>{employee.employee_id}</small></Link>)}</div> : <div className="positive-state"><strong>100%</strong><span>{locale === "ru" ? "Для всех есть следующий шаг" : "Everyone has a next step"}</span></div>}</section>
    </div>
    <section className="panel table-panel"><span className="section-label">Engagement</span><h2>{t.participation}</h2><div className="table-wrap"><table><thead><tr><th>Activity</th><th>{t.completed}</th><th>{t.missed}</th><th>{t.declined}</th><th>{t.completionRate}</th></tr></thead><tbody>{data.participation.map((item) => <tr key={item.event_code}><td><strong>{item.event_name}</strong><small>{item.event_code}</small></td><td>{item.completed}</td><td>{item.missed}</td><td>{item.declined}</td><td><span className="rate-pill">{item.completion_rate}%</span></td></tr>)}</tbody></table></div></section>
  </div>;
}
