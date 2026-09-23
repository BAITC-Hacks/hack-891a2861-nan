"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useLocale } from "@/components/locale-provider";
import { api } from "@/lib/api";
import type { EmployeeSummary } from "@/lib/types";

export default function HomePage() {
  const { t } = useLocale();
  const [employees, setEmployees] = useState<EmployeeSummary[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.employees().then(setEmployees).catch((reason) => setError(String(reason)));
  }, []);

  return (
    <div className="page shell">
      <section className="hero">
        <div>
          <span className="eyebrow">Halyk · HackAlem AI</span>
          <h1>{t.chooseProfile}</h1>
          <p>{t.subtitle}</p>
        </div>
        <div className="hero-orbit" aria-hidden="true"><span>AI</span></div>
      </section>
      {error && <div className="error-banner">{t.error}: {error}</div>}
      <section className="profile-grid">
        {employees.map((employee, index) => (
          <Link className="profile-card" href={`/employee/${employee.employee_id}`} key={employee.employee_id}>
            <span className={`avatar avatar-${(index % 4) + 1}`}>{employee.display_name.split(" ").map((x) => x[0]).join("")}</span>
            <div>
              <strong>{employee.display_name}</strong>
              <p>{employee.role} · {employee.grade}</p>
              <small>{employee.employee_id} · {employee.tenure_months} months</small>
            </div>
            <span className="arrow">→</span>
          </Link>
        ))}
        {!employees.length && !error && <p className="muted">{t.loading}</p>}
      </section>
    </div>
  );
}
