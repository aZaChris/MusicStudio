import Link from "next/link";

import { LanguageToggle } from "@/components/LanguageToggle";
import { ThemeToggle } from "@/components/ThemeToggle";
import { signOutAction } from "@/app/actions/auth";
import { auth } from "@/lib/auth";
import { t, type TranslationKey } from "@/lib/i18n";
import { getLocale } from "@/lib/get-locale";
import { getActor } from "@/lib/rbac";
import { listStudentLessons } from "@/lib/services/lessons";
import { listPaymentsForActor } from "@/lib/services/payments";
import { listStudentsForActor } from "@/lib/services/students";

function capitalizeStatus(s: string) {
  return s
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join("");
}

export default async function ParentPortalPage({
  searchParams,
}: {
  searchParams: Promise<{ student?: string }>;
}) {
  const session = await auth();
  const locale = await getLocale();
  if (!session) return null;

  const actor = await getActor(Number(session.user.id), session.user.role);
  const students = await listStudentsForActor(actor);

  if (students.length === 0) {
    return <p style={{ padding: 36 }}>{t(locale, "parent.noStudents")}</p>;
  }

  const { student: studentParam } = await searchParams;
  const activeId = studentParam ? Number(studentParam) : students[0].id;

  const [lessons, payments] = await Promise.all([
    listStudentLessons(actor, activeId),
    listPaymentsForActor(actor),
  ]);
  const studentPayments = payments.filter((p) => p.studentId === activeId);

  const dateFormatter = new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" });

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "36px 24px", display: "flex", flexDirection: "column", gap: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 style={{ fontFamily: "var(--ms-font-heading)", fontSize: 22, margin: 0 }}>{t(locale, "parent.portalTitle")}</h1>
        <div style={{ display: "flex", gap: 8 }}>
          <ThemeToggle label={t(locale, "theme.toggle")} />
          <LanguageToggle locale={locale} />
          <form action={signOutAction}>
            <button type="submit">{t(locale, "auth.logout")}</button>
          </form>
        </div>
      </div>

      {students.length > 1 && (
        <div style={{ display: "flex", gap: 8 }}>
          {students.map((s) => (
            <Link
              key={s.id}
              href={`/parent?student=${s.id}`}
              style={{
                padding: "6px 14px",
                borderRadius: 999,
                border: "1px solid var(--ms-border)",
                background: activeId === s.id ? "var(--ms-accent)" : "var(--ms-surface)",
                color: activeId === s.id ? "white" : "inherit",
                textDecoration: "none",
              }}
            >
              {s.fullName}
            </Link>
          ))}
        </div>
      )}

      <section>
        <h2 style={{ fontSize: 16, fontFamily: "var(--ms-font-heading)" }}>
          {t(locale, "parent.upcomingLessons")} / {t(locale, "parent.attendance")}
        </h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {lessons.map((lesson) => (
            <div
              key={lesson.id}
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: 12,
                padding: "10px 14px",
                border: "1px solid var(--ms-border)",
                borderRadius: "var(--ms-radius-sm)",
              }}
            >
              <span>{dateFormatter.format(new Date(lesson.startTime))}</span>
              <span>{t(locale, `lesson.status${capitalizeStatus(lesson.status)}` as TranslationKey)}</span>
              {lesson.notes && <span style={{ color: "var(--ms-text-muted)" }}>{lesson.notes}</span>}
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 style={{ fontSize: 16, fontFamily: "var(--ms-font-heading)" }}>{t(locale, "parent.paymentStatus")}</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {studentPayments.map((p) => (
            <div
              key={p.id}
              style={{
                display: "flex",
                justifyContent: "space-between",
                padding: "10px 14px",
                border: "1px solid var(--ms-border)",
                borderRadius: "var(--ms-radius-sm)",
              }}
            >
              <span>{p.date}</span>
              <span>{p.amount}</span>
              <span>{t(locale, `payments.status${capitalizeStatus(p.status)}` as TranslationKey)}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
