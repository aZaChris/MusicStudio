import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { apiFetch, tokenStorage } from "./api";
import { storage } from "./storage";

export type Role = "teacher" | "studio_owner" | "parent";

export interface Me {
  id: number;
  email: string;
  role: Role;
  preferredLanguage: "en" | "it";
}

const USER_KEY = "musicstudio-user";

interface AuthState {
  user: Me | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const [token, cachedUser] = await Promise.all([tokenStorage.get(), storage.get(USER_KEY)]);
      // ponytail: cached at login time, not re-verified on each launch — if
      // role/profile changes server-side, a re-login picks it up. Add
      // GET /api/v1/auth/me (requireActor() already supports Bearer auth
      // generically) if that staleness window ever matters.
      if (token && cachedUser) setUser(JSON.parse(cachedUser));
      setIsLoading(false);
    })();
  }, []);

  const login = async (email: string, password: string) => {
    const { token, user: loggedInUser } = await apiFetch<{ token: string; user: Me }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    await Promise.all([tokenStorage.set(token), storage.set(USER_KEY, JSON.stringify(loggedInUser))]);
    setUser(loggedInUser);
  };

  const logout = async () => {
    await Promise.all([tokenStorage.clear(), storage.remove(USER_KEY)]);
    setUser(null);
  };

  return <AuthContext.Provider value={{ user, isLoading, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
