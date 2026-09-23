"use client";

import { use, useCallback, useEffect, useState } from "react";
import { ProgressRing } from "@/components/progress-ring";
import { useLocale } from "@/components/locale-provider";
import { api } from "@/lib/api";
import type { EmployeeProfile, Recommendation } from "@/lib/types";

export default function EmployeePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { locale, t } = useLocale();
  const [profile, setProfile] = useState<EmployeeProfile | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const [employee, result] = await Promise.all([
        api.employee(id, locale),
        api.recommendations(id, locale),
      ]);
      setProfile(employee);
      setRecommendations(result.recommendations);
    } catch (reason) {
      setError(String(reason));
    }
  }, [id, locale]);

  useEffect(() => {
    // Network results update the page state after the request resolves.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  async function complete(eventId: string) {
    setBusy(eventId);
    try {
      await api.complete(id, eventId);
      await load();
    } catch (reason) {
      setError(String(reason));
    } finally {
      setBusy("");
    }
  }

  if (!profile) return <div className="page shell"><p>{error || t.loading}</p></div>;
  const trajectory = profile.trajectory;

  return (
    <div className="page shell">
      {error && <div className="error-banner">{t.error}: {error}</div>}
      <section className="profile-heading">
        <div className="avatar avatar-large">{profile.display_name.split(" ").map((x) => x[0]).join("")}</div>
        <div><span className="eyebrow">{profile.employee_id}</span><h1>{profile.display_name}</h1><p>{profile.role.name} · {profile.grade.name} · {profile.tenure_months} months</p></div>
      </section>

      <section className="trajectory-card">
        <div><span className="section-label">{t.trajectory}</span><h2>{trajectory.current_grade.name} <span>→</span> {trajectory.target_grade?.name ?? "Top grade"}</h2><p>{t.nextGrade}: {trajectory.target_grade?.name ?? "—"}</p></div>
        <div className="readiness"><ProgressRing value={trajectory.readiness_percent} /><span>{t.readiness}</span></div>
      </section>

      <section><div className="section-title"><div><span className="section-label">AI decision layer</span><h2>{t.recommendations}</h2></div><span className="engine-badge">Hybrid v1 · evidence grounded</span></div>
        <div className="recommendations">
          {recommendations.map((item) => (
            <article className="recommendation-card" key={item.id}>
              <div className="recommendation-rank">0{item.rank}</div>
              <div className="recommendation-content">
                <div className="recommendation-top"><div><span className="format-chip">{item.event.format}</span><h3>{item.event.name}</h3></div><span className="score">{Math.round(item.score * 100)} match</span></div>
                <p>{item.event.description}</p>
                <div className="impact-row">{item.impacted_skills.map((skill) => <span key={skill.skill_code}>{skill.skill_name}: {skill.current_level} → {Math.min(skill.current_level + skill.gain, skill.max_level)}</span>)}<span>{item.event.duration_hours} {t.hours}</span></div>
                <details><summary>{t.why}</summary><div className="reason-grid">{item.explanation.reasons.map((reason) => <div key={reason.factor}><small>{reason.factor.replace("_", " ")}</small><strong>{reason.message}</strong></div>)}</div></details>
                <button className="primary-button" disabled={Boolean(busy)} onClick={() => complete(item.event.code)}>{busy === item.event.code ? t.completing : t.complete}</button>
              </div>
            </article>
          ))}
          {!recommendations.length && <div className="empty-state">{t.noRecommendations}</div>}
        </div>
      </section>

      <div className="two-column">
        <section className="panel"><span className="section-label">{t.skills}</span><h2>{t.skills}</h2><div className="skill-list">{profile.skills.sort((a,b) => a.name.localeCompare(b.name)).map((skill) => { const gap = trajectory.gaps.find((x) => x.skill_code === skill.code); return <div className="skill-row" key={skill.code}><div><strong>{skill.name}</strong><small>{skill.kind}{gap ? ` · ${t.priority} ${gap.priority}` : ""}</small></div><div className="level-dots" aria-label={`${skill.level} of 5`}>{[1,2,3,4,5].map((level) => <i className={level <= skill.level ? "filled" : ""} key={level} />)}</div><span>{skill.level}/5</span></div>; })}</div></section>
        <section className="panel"><span className="section-label">{t.history}</span><h2>{t.history}</h2><div className="timeline">{profile.activities.map((activity) => <div key={activity.id}><i className={`status-${activity.status}`} /><div><strong>{activity.event_name}</strong><small>{new Date(activity.occurred_at).toLocaleDateString(locale)} · {activity.status}</small></div></div>)}</div></section>
      </div>
    </div>
  );
}
