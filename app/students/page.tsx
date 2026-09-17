import Link from "next/link";

import { Sidebar } from "@/components/Sidebar";
import { auth } from "@/lib/auth";
import { t, type TranslationKey } from "@/lib/i18n";
import { getLocale } from "@/lib/get-locale";
import { getActor } from "@/lib/rbac";
import { listStudentsForActor } from "@/lib/services/students";

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export default async function StudentsPage() {
  const session = await auth();
  const locale = await getLocale();
  if (!session) return null;

  const actor = await getActor(Number(session.user.id), session.user.role);
  const students = await listStudentsForActor(actor);

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <div style={{ flex: 1, padding: "36px 44px", maxWidth: 1280 }}>
        <h1 style={{ fontFamily: "var(--ms-font-heading)", fontSize: 22, fontWeight: 600 }}>
          {t(locale, "roster.title")}
        </h1>

        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left", fontSize: 12.5, color: "var(--ms-text-muted)" }}>
              <th style={{ padding: "10px 8px" }}>{t(locale, "roster.student")}</th>
              <th style={{ padding: "10px 8px" }}>{t(locale, "roster.package")}</th>
              <th style={{ padding: "10px 8px" }}>{t(locale, "roster.remaining")}</th>
              <th style={{ padding: "10px 8px" }}>{t(locale, "roster.paymentStatus")}</th>
            </tr>
          </thead>
          <tbody>
            {students.map((student) => (
              <tr key={student.id} style={{ borderTop: "1px solid var(--ms-border)", fontSize: 14 }}>
                <td style={{ padding: "10px 8px" }}>
                  <Link href={`/students/${student.id}`}>{student.fullName}</Link>
                </td>
                <td style={{ padding: "10px 8px" }}>
                  {student.activePackage
                    ? `${student.activePackage.lessonsRemaining}/${student.activePackage.totalLessons}`
                    : "—"}
                </td>
                <td style={{ padding: "10px 8px" }}>
                  {student.activePackage?.isLow && (
                    <span
                      style={{
                        background: "var(--ms-warning-bg)",
                        color: "var(--ms-warning-text)",
                        borderRadius: 999,
                        padding: "2px 8px",
                        fontSize: 12,
                      }}
                    >
                      {t(locale, "roster.lowPackage")}
                    </span>
                  )}
                </td>
                <td style={{ padding: "10px 8px" }}>
                  {student.paymentStatus
                    ? t(locale, `payments.status${capitalize(student.paymentStatus)}` as TranslationKey)
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
