import { notFound } from "next/navigation";

import { Sidebar } from "@/components/Sidebar";
import { auth } from "@/lib/auth";
import { t, type TranslationKey } from "@/lib/i18n";
import { getLocale } from "@/lib/get-locale";
import { getActor } from "@/lib/rbac";
import { listStudentLessons } from "@/lib/services/lessons";
import { getStudentForActor } from "@/lib/services/students";

function capitalizeStatus(s: string) {
  return s
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join("");
}

export default async function StudentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const session = await auth();
  const locale = await getLocale();
  if (!session) return null;

  const { id } = await params;
  const actor = await getActor(Number(session.user.id), session.user.role);
  const student = await getStudentForActor(actor, Number(id));
  if (!student) notFound();

  const lessons = await listStudentLessons(actor, student.id);
  const dateFormatter = new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" });

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <div style={{ flex: 1, padding: "36px 44px", maxWidth: 1280 }}>
        <h1 style={{ fontFamily: "var(--ms-font-heading)", fontSize: 22, fontWeight: 600 }}>{student.fullName}</h1>
        <p style={{ color: "var(--ms-text-muted)" }}>{student.instrument}</p>

        {student.activePackage && (
          <div
            style={{
              background: "var(--ms-surface)",
              border: "1px solid var(--ms-border)",
              borderRadius: "var(--ms-radius-lg)",
              padding: 16,
              marginBottom: 24,
              maxWidth: 320,
            }}
          >
            <div style={{ fontWeight: 700 }}>{t(locale, "roster.package")}</div>
            <div>
              {student.activePackage.lessonsRemaining}/{student.activePackage.totalLessons} ({student.activePackage.status})
            </div>
          </div>
        )}

        <h2 style={{ fontSize: 16, fontFamily: "var(--ms-font-heading)" }}>{t(locale, "dashboard.upcoming")}</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {lessons.map((lesson) => (
            <div
              key={lesson.id}
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: 12,
                padding: "8px 12px",
                border: "1px solid var(--ms-border)",
                borderRadius: 8,
              }}
            >
              <span>{dateFormatter.format(new Date(lesson.startTime))}</span>
              <span>{t(locale, `lesson.status${capitalizeStatus(lesson.status)}` as TranslationKey)}</span>
              {lesson.notes && <span style={{ color: "var(--ms-text-muted)" }}>{lesson.notes}</span>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
