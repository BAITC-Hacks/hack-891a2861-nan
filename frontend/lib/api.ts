import type { AuthUser, EmployeeProfile, EmployeeSummary, HRDashboard, Locale, Recommendation } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:18000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = typeof window !== "undefined" ? window.localStorage.getItem("cq-token") : null;
  const headers = new Headers(init?.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_URL}${path}`, { cache: "no-store", ...init, headers });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload?.error?.details ?? `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  login: (username: string, password: string) =>
    request<{ token: string; user: AuthUser }>("/auth/login/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    }),
  me: () => request<AuthUser>("/auth/me/"),
  employees: () => request<EmployeeSummary[]>("/employees/"),
  employee: (id: string, locale: Locale) =>
    request<EmployeeProfile>(`/employees/${id}/?locale=${locale}`),
  recommendations: (id: string, locale: Locale) =>
    request<{ employee_id: string; recommendations: Recommendation[] }>(
      `/employees/${id}/recommendations/?locale=${locale}`,
    ),
  complete: (employeeId: string, eventId: string) =>
    request(`/employees/${employeeId}/activities/${eventId}/complete/`, {
      method: "POST",
      headers: {
        "Idempotency-Key": crypto.randomUUID(),
        "Content-Type": "application/json",
      },
      body: "{}",
    }),
  dashboard: (locale: Locale) =>
    request<HRDashboard>(`/hr/dashboard/?locale=${locale}`),
  importDataset: async (data: FormData) =>
    request<{ status: string; counts: Record<string, number> }>("/admin/import/", {
      method: "POST",
      body: data,
    }),
};
