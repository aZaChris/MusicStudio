import { Sidebar } from "@/components/Sidebar";
import { WeekGrid } from "@/components/WeekGrid";
import { auth } from "@/lib/auth";
import { t } from "@/lib/i18n";
import { getLocale } from "@/lib/get-locale";
import { getActor } from "@/lib/rbac";
import { getDashboard } from "@/lib/services/dashboard";

export default async function DashboardPage() {
  const session = await auth();
  const locale = await getLocale();
  if (!session) return null;

  const actor = await getActor(Number(session.user.id), session.user.role);
  const dashboard = await getDashboard(actor);

  const timeFormatter = new Intl.DateTimeFormat(locale, { hour: "2-digit", minute: "2-digit" });

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <div style={{ flex: 1, padding: "36px 44px", maxWidth: 1280, display: "flex", flexDirection: "column", gap: 28 }}>
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
          <div style={{ fontFamily: "var(--ms-font-heading)", fontWeight: 600, fontSize: 26 }}>
            {t(locale, "dashboard.greeting", { name: session.user.email.split("@")[0] })}
          </div>
          <div style={{ display: "flex", gap: 28 }}>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontFamily: "var(--ms-font-heading)", fontWeight: 700, fontSize: 22 }}>
                {dashboard.activeStudentsCount}
              </div>
              <div style={{ fontSize: 12.5, color: "var(--ms-text-muted)" }}>{t(locale, "dashboard.activeStudents")}</div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div
                style={{ fontFamily: "var(--ms-font-heading)", fontWeight: 700, fontSize: 22, color: "var(--ms-danger-text)" }}
              >
                {dashboard.pendingPaymentsCount}
              </div>
              <div style={{ fontSize: 12.5, color: "var(--ms-text-muted)" }}>{t(locale, "dashboard.pendingPayments")}</div>
            </div>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: 24, alignItems: "start" }}>
          <div
            style={{
              background: "var(--ms-surface)",
              borderRadius: "var(--ms-radius-lg)",
              border: "1px solid var(--ms-border)",
              padding: 20,
              overflowX: "auto",
            }}
          >
            <div style={{ fontFamily: "var(--ms-font-heading)", fontWeight: 600, fontSize: 16, marginBottom: 14 }}>
              {t(locale, "dashboard.thisWeek")}
            </div>
            <WeekGrid lessons={dashboard.week} locale={locale} />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div
              style={{
                background: "var(--ms-surface)",
                borderRadius: "var(--ms-radius-lg)",
                border: "1px solid var(--ms-border)",
                padding: 20,
              }}
            >
              <div style={{ fontFamily: "var(--ms-font-heading)", fontWeight: 600, fontSize: 16, marginBottom: 12 }}>
                {t(locale, "dashboard.upcoming")}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {dashboard.upcoming.map((lesson) => (
                  <div key={lesson.id} style={{ display: "flex", justifyContent: "space-between", fontSize: 13.5 }}>
                    <span>
                      {lesson.studentName} {lesson.studentLastName}
                    </span>
                    <span style={{ color: "var(--ms-text-muted)" }}>{timeFormatter.format(new Date(lesson.startTime))}</span>
                  </div>
                ))}
              </div>
            </div>

            {dashboard.lowPackageStudents.length > 0 && (
              <div
                style={{
                  background: "var(--ms-warning-bg)",
                  color: "var(--ms-warning-text)",
                  borderRadius: "var(--ms-radius-lg)",
                  padding: 16,
                  fontSize: 13.5,
                }}
              >
                {dashboard.lowPackageStudents.map((s) => s.fullName).join(", ")} — {t(locale, "roster.lowPackage")}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
