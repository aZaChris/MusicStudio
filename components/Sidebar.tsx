import Link from "next/link";

import { signOutAction } from "@/app/actions/auth";
import { auth } from "@/lib/auth";
import { t } from "@/lib/i18n";
import { getLocale } from "@/lib/get-locale";
import { LanguageToggle } from "./LanguageToggle";
import { ThemeToggle } from "./ThemeToggle";

const NAV_ITEMS = [
  { href: "/dashboard", icon: "▤", key: "nav.dashboard" as const },
  { href: "/students", icon: "☰", key: "nav.students" as const },
  { href: "/payments", icon: "€", key: "nav.payments" as const },
];

export async function Sidebar() {
  const session = await auth();
  const locale = await getLocale();

  return (
    <nav
      style={{
        width: 232,
        flex: "none",
        background: "var(--ms-surface-muted)",
        borderRight: "1px solid var(--ms-border)",
        display: "flex",
        flexDirection: "column",
        padding: "24px 16px",
        gap: 28,
        minHeight: "100vh",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "0 8px" }}>
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: "var(--ms-radius-sm)",
            background: "var(--ms-accent)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "white",
            fontSize: 18,
          }}
        >
          ♪
        </div>
        <div style={{ fontFamily: "var(--ms-font-heading)", fontWeight: 600, fontSize: 17 }}>
          MusicStudio
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            style={{
              cursor: "pointer",
              padding: "10px 14px",
              borderRadius: "var(--ms-radius-sm)",
              fontWeight: 700,
              fontSize: 14.5,
              display: "flex",
              alignItems: "center",
              gap: 10,
              textDecoration: "none",
              color: "inherit",
            }}
          >
            <span style={{ opacity: 0.75 }}>{item.icon}</span> {t(locale, item.key)}
          </Link>
        ))}
      </div>

      <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ display: "flex", gap: 8 }}>
          <ThemeToggle label={t(locale, "theme.toggle")} />
          <LanguageToggle locale={locale} />
        </div>
        <div
          style={{
            padding: 14,
            borderRadius: "var(--ms-radius-md)",
            background: "var(--ms-border)",
            display: "flex",
            flexDirection: "column",
            gap: 2,
          }}
        >
          <div style={{ fontWeight: 800, fontSize: 13.5 }}>{session?.user.email}</div>
          <form action={signOutAction}>
            <button type="submit" style={{ fontSize: 12.5, textAlign: "left" }}>
              {t(locale, "auth.logout")}
            </button>
          </form>
        </div>
      </div>
    </nav>
  );
}
