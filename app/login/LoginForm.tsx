"use client";

import { useActionState } from "react";

import { signInAction } from "@/app/actions/auth";
import type { Locale } from "@/lib/i18n";
import { t } from "@/lib/i18n";

export function LoginForm({ locale }: { locale: Locale }) {
  const [error, formAction, pending] = useActionState(signInAction, null);

  return (
    <form
      action={formAction}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 12,
        width: 320,
        padding: 28,
        borderRadius: "var(--ms-radius-lg)",
        border: "1px solid var(--ms-border)",
        background: "var(--ms-surface)",
        boxShadow: "0 8px 24px oklch(0% 0 0 / 0.06)",
      }}
    >
      <h1 style={{ fontFamily: "var(--ms-font-heading)", fontSize: 20, margin: "0 0 8px" }}>MusicStudio</h1>
      <label>
        {t(locale, "auth.email")}
        <input type="email" name="email" required />
      </label>
      <label>
        {t(locale, "auth.password")}
        <input type="password" name="password" required />
      </label>
      {error && <p style={{ color: "var(--ms-danger-text)", fontSize: 13, margin: 0 }}>Invalid credentials</p>}
      <button type="submit" className="primary" disabled={pending} style={{ marginTop: 8 }}>
        {t(locale, "auth.login")}
      </button>
    </form>
  );
}
