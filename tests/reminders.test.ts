import { beforeEach, describe, expect, it } from "vitest";

import { getDb } from "@/lib/db";
import { lessons } from "@/lib/db/schema";
import { sendLessonReminders } from "@/lib/services/reminders";
import { eq } from "drizzle-orm";
import {
  createLesson,
  createParentAccount,
  createStudent,
  createTeacher,
  linkParentToStudent,
  resetDb,
} from "./helpers";

beforeEach(async () => {
  await resetDb();
});

describe("sendLessonReminders", () => {
  it("sends exactly once for a lesson ~24h out and stamps reminderSentAt", async () => {
    const teacher = await createTeacher();
    const student = await createStudent(teacher.id);
    const parent = await createParentAccount();
    await linkParentToStudent(parent.id, student.id);
    const lesson = await createLesson(student.id, teacher.id, {
      startTime: new Date(Date.now() + (23 * 60 + 50) * 60 * 1000),
    });

    const { sent } = await sendLessonReminders();

    expect(sent).toBe(1);
    const db = getDb();
    const [updated] = await db.select().from(lessons).where(eq(lessons.id, lesson.id));
    expect(updated.reminderSentAt).not.toBeNull();
  });

  it("is idempotent on a second sweep of the same window", async () => {
    const teacher = await createTeacher();
    const student = await createStudent(teacher.id);
    const parent = await createParentAccount();
    await linkParentToStudent(parent.id, student.id);
    await createLesson(student.id, teacher.id, {
      startTime: new Date(Date.now() + (23 * 60 + 50) * 60 * 1000),
    });

    const first = await sendLessonReminders();
    const second = await sendLessonReminders();

    expect(first.sent).toBe(1);
    expect(second.sent).toBe(0);
  });

  it("skips a lesson outside the 24h window", async () => {
    const teacher = await createTeacher();
    const student = await createStudent(teacher.id);
    await createLesson(student.id, teacher.id, { startTime: new Date(Date.now() + 48 * 60 * 60 * 1000) });

    const { sent } = await sendLessonReminders();

    expect(sent).toBe(0);
  });

  it("skips a cancelled lesson even inside the window", async () => {
    const teacher = await createTeacher();
    const student = await createStudent(teacher.id);
    await createLesson(student.id, teacher.id, {
      startTime: new Date(Date.now() + (23 * 60 + 50) * 60 * 1000),
      status: "cancelled",
    });

    const { sent } = await sendLessonReminders();

    expect(sent).toBe(0);
  });
});
