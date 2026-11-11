import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import { ApiError, apiFetch, session } from "./api/client";
import type { LoginResponse, Me, TokenPair } from "./api/types";
import type { TranslationKey } from "./i18n";

/** "unreachable": a session is stored but the server could not confirm it (offline). */
export type AuthStatus = "loading" | "signed-in" | "signed-out" | "unreachable";

interface AuthState {
  user: Me | null;
  status: AuthStatus;
  /** Why the user is on the login screen, e.g. the session expired. */
  notice: TranslationKey | null;
  /** Resolves with an `mfaToken` when a second step is due, otherwise signs in. */
  login: (email: string, password: string) => Promise<{ mfaToken: string | null }>;
  verifyMfa: (mfaToken: string, code: string) => Promise<void>;
  logout: () => Promise<void>;
  retry: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<Me | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [notice, setNotice] = useState<TranslationKey | null>(null);

  // Startup: never trust a cached user; ask the server who we are (audit issue 6).
  // Returns the outcome instead of setting state, so the effect applies it in a callback.
  const check = useCallback(async (): Promise<{ user: Me | null; status: AuthStatus }> => {
    if (!(await session.refreshToken())) return { user: null, status: "signed-out" };
    try {
      return { user: await apiFetch<Me>("/auth/me/"), status: "signed-in" };
    } catch (error) {
      if (error instanceof ApiError && error.status === 0) return { user: null, status: "unreachable" };
      await session.clear();
      return { user: null, status: "signed-out" };
    }
  }, []);

  const apply = useCallback((result: { user: Me | null; status: AuthStatus }) => {
    setUser(result.user);
    setStatus(result.status);
  }, []);

  useEffect(() => {
    let mounted = true;
    void check().then((result) => mounted && apply(result));
    return () => {
      mounted = false;
    };
  }, [check, apply]);

  // The client could not renew the session: back to login, and drop every cached response.
  useEffect(
    () =>
      session.onExpired(() => {
        queryClient.clear();
        setUser(null);
        setNotice("auth.sessionExpired");
        setStatus("signed-out");
      }),
    [queryClient],
  );

  const finishSignIn = useCallback(
    async (tokens: { access: string; refresh: string }) => {
      await session.start(tokens);
      const me = await apiFetch<Me>("/auth/me/");
      queryClient.clear(); // nothing from a previous user survives a sign-in
      setUser(me);
      setNotice(null);
      setStatus("signed-in");
    },
    [queryClient],
  );

  const login = useCallback(
    async (email: string, password: string) => {
      const answer = await apiFetch<LoginResponse>("/auth/token/", { method: "POST", body: { email, password }, auth: false });
      // Owners and teachers with MFA on get a short-lived token instead of the token pair.
      if (answer.mfa_required && answer.mfa_token) return { mfaToken: answer.mfa_token };
      await finishSignIn(answer as TokenPair);
      return { mfaToken: null };
    },
    [finishSignIn],
  );

  const verifyMfa = useCallback(
    async (mfaToken: string, code: string) => {
      const tokens = await apiFetch<TokenPair>("/auth/mfa/verify/", {
        method: "POST",
        body: { mfa_token: mfaToken, code },
        auth: false,
      });
      await finishSignIn(tokens);
    },
    [finishSignIn],
  );

  const logout = useCallback(async () => {
    // The body is read at send time: if the access token had expired, the first call
    // refreshes (rotating the refresh token) and its body holds the old, now blacklisted
    // token -> 400. The second call sends the rotated one.
    const sendLogout = async () => {
      const refresh = await session.refreshToken();
      if (refresh) await apiFetch("/auth/logout/", { method: "POST", body: { refresh } });
    };
    try {
      await sendLogout();
    } catch (error) {
      if (error instanceof ApiError && error.status === 400) await sendLogout().catch(() => undefined);
      // Any other failure (offline...): still sign out locally, as the user asked.
    }
    await session.clear();
    queryClient.clear();
    setUser(null);
    setNotice(null);
    setStatus("signed-out");
  }, [queryClient]);

  const retry = useCallback(() => {
    setStatus("loading");
    void check().then(apply);
  }, [check, apply]);

  return (
    <AuthContext.Provider value={{ user, status, notice, login, verifyMfa, logout, retry }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
