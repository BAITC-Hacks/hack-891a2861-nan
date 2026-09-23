import type { EmployeeProfile, EmployeeSummary, HRDashboard, Locale, Recommendation } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { cache: "no-store", ...init });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload?.error?.details ?? `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  employees: () => request<EmployeeSummary[]>("/employees/", { headers: { "X-Demo-Role": "hr" } }),
  employee: (id: string, locale: Locale) =>
    request<EmployeeProfile>(`/employees/${id}/?locale=${locale}`, {
      headers: { "X-Employee-ID": id },
    }),
  recommendations: (id: string, locale: Locale) =>
    request<{ employee_id: string; recommendations: Recommendation[] }>(
      `/employees/${id}/recommendations/?locale=${locale}`,
      { headers: { "X-Employee-ID": id } },
    ),
  complete: (employeeId: string, eventId: string) =>
    request(`/employees/${employeeId}/activities/${eventId}/complete/`, {
      method: "POST",
      headers: {
        "X-Employee-ID": employeeId,
        "Idempotency-Key": crypto.randomUUID(),
        "Content-Type": "application/json",
      },
      body: "{}",
    }),
  dashboard: (locale: Locale) =>
    request<HRDashboard>(`/hr/dashboard/?locale=${locale}`, {
      headers: { "X-Demo-Role": "hr" },
    }),
  importDataset: async (data: FormData) =>
    request<{ status: string; counts: Record<string, number> }>("/admin/import/", {
      method: "POST",
      headers: { "X-Demo-Role": "hr" },
      body: data,
    }),
};
