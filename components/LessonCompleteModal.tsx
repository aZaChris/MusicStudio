"use client";

import { useState, useTransition } from "react";

import { completeLessonAction } from "@/app/actions/lessons";
import type { Locale } from "@/lib/i18n";
import { t } from "@/lib/i18n";

export function LessonCompleteModal({
  lessonId,
  studentName,
  locale,
  onClose,
}: {
  lessonId: number;
  studentName: string;
  locale: Locale;
  onClose: () => void;
}) {
  const [note, setNote] = useState("");
  const [pending, startTransition] = useTransition();

  const handleComplete = () => {
    startTransition(async () => {
      await completeLessonAction(lessonId, note);
      onClose();
    });
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.3)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 10,
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "var(--ms-surface)",
          borderRadius: "var(--ms-radius-lg)",
          padding: 24,
          width: 360,
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        <h2 style={{ margin: 0, fontFamily: "var(--ms-font-heading)", fontSize: 18 }}>{studentName}</h2>
        <label>
          {t(locale, "lesson.note")}
          <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={3} style={{ width: "100%" }} />
        </label>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button type="button" onClick={onClose}>
            {t(locale, "lesson.cancel")}
          </button>
          <button type="button" onClick={handleComplete} disabled={pending}>
            {t(locale, "lesson.markComplete")}
          </button>
        </div>
      </div>
    </div>
  );
}
