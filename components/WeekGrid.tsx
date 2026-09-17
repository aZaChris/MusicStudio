"use client";

import { useState } from "react";

import type { Locale } from "@/lib/i18n";
import { LessonCompleteModal } from "./LessonCompleteModal";

export interface WeekLesson {
  id: number;
  studentName: string;
  studentLastName: string;
  startTime: string | Date;
  status: string;
}

const DAY_ORDER = [1, 2, 3, 4, 5, 6, 0]; // Monday-first

function groupByDay(lessons: WeekLesson[]) {
  const byDay: Record<number, WeekLesson[]> = { 0: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: [] };
  for (const lesson of lessons) byDay[new Date(lesson.startTime).getDay()].push(lesson);
  return byDay;
}

export function WeekGrid({ lessons, locale }: { lessons: WeekLesson[]; locale: Locale }) {
  const [active, setActive] = useState<WeekLesson | null>(null);
  const byDay = groupByDay(lessons);

  const dayFormatter = new Intl.DateTimeFormat(locale, { weekday: "short" });
  const timeFormatter = new Intl.DateTimeFormat(locale, { hour: "2-digit", minute: "2-digit" });

  return (
    <>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, minmax(120px, 1fr))", gap: 8 }}>
        {DAY_ORDER.map((day) => (
          <div key={day}>
            <div
              style={{
                textAlign: "center",
                fontSize: 12,
                fontWeight: 800,
                color: "var(--ms-text-muted)",
                marginBottom: 6,
              }}
            >
              {dayFormatter.format(new Date(2024, 0, day === 0 ? 7 : day))}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {byDay[day].map((lesson) => (
                <button
                  key={lesson.id}
                  type="button"
                  disabled={lesson.status !== "scheduled"}
                  onClick={() => setActive(lesson)}
                  style={{
                    textAlign: "left",
                    fontSize: 12,
                    padding: "6px 8px",
                    borderRadius: 8,
                    border: "1px solid var(--ms-border)",
                    background: lesson.status === "completed" ? "var(--ms-success-bg)" : "var(--ms-surface-muted)",
                    color: lesson.status === "completed" ? "var(--ms-success-text)" : "inherit",
                  }}
                >
                  <div style={{ fontWeight: 700 }}>{timeFormatter.format(new Date(lesson.startTime))}</div>
                  <div>
                    {lesson.studentName} {lesson.studentLastName}
                  </div>
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      {active && (
        <LessonCompleteModal
          lessonId={active.id}
          studentName={`${active.studentName} ${active.studentLastName}`}
          locale={locale}
          onClose={() => setActive(null)}
        />
      )}
    </>
  );
}
