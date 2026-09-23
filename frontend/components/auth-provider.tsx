"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { AuthUser } from "@/lib/types";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<AuthUser>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function restoreSession() {
      try {
        if (window.localStorage.getItem("cq-token")) setUser(await api.me());
      } catch {
        window.localStorage.removeItem("cq-token");
      } finally {
        setLoading(false);
      }
    }
    void restoreSession();
  }, []);

  const value = useMemo(() => ({
    user,
    loading,
    login: async (username: string, password: string) => {
      const result = await api.login(username, password);
      window.localStorage.setItem("cq-token", result.token);
      setUser(result.user);
      return result.user;
    },
    logout: () => {
      window.localStorage.removeItem("cq-token");
      setUser(null);
      router.push("/");
      router.refresh();
    },
  }), [user, loading, router]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider");
  return value;
}
