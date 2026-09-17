import { and, asc, desc, eq, gt, gte, lt, ne, sql } from "drizzle-orm";

import { getDb } from "../db";
import { lessons, packages, students } from "../db/schema";
import type { Actor } from "../rbac";
import { lessonScope } from "../rbac";

function weekBounds(anchor: Date) {
  const day = (anchor.getDay() + 6) % 7; // Monday = 0
  const monday = new Date(anchor);
  monday.setHours(0, 0, 0, 0);
  monday.setDate(monday.getDate() - day);
  const nextMonday = new Date(monday);
  nextMonday.setDate(monday.getDate() + 7);
  return { start: monday, end: nextMonday };
}

export async function listWeekLessons(actor: Actor, anchor: Date = new Date()) {
  const db = getDb();
  const { start, end } = weekBounds(anchor);
  return db
    .select({
      id: lessons.id,
      studentId: lessons.studentId,
      studentName: students.firstName,
      studentLastName: students.lastName,
      teacherId: lessons.teacherId,
      packageId: lessons.packageId,
      startTime: lessons.startTime,
      durationMinutes: lessons.durationMinutes,
      status: lessons.status,
      notes: lessons.notes,
    })
    .from(lessons)
    .innerJoin(students, eq(lessons.studentId, students.id))
    .where(and(lessonScope(actor), gte(lessons.startTime, start), lt(lessons.startTime, end)))
    .orderBy(asc(lessons.startTime));
}

export async function listUpcomingLessons(actor: Actor, limit = 3) {
  const db = getDb();
  return db
    .select({
      id: lessons.id,
      studentId: lessons.studentId,
      studentName: students.firstName,
      studentLastName: students.lastName,
      startTime: lessons.startTime,
      status: lessons.status,
    })
    .from(lessons)
    .innerJoin(students, eq(lessons.studentId, students.id))
    .where(and(lessonScope(actor), eq(lessons.status, "scheduled"), gte(lessons.startTime, new Date())))
    .orderBy(asc(lessons.startTime))
    .limit(limit);
}

export async function listStudentLessons(actor: Actor, studentId: number) {
  const db = getDb();
  return db
    .select()
    .from(lessons)
    .where(and(lessonScope(actor), eq(lessons.studentId, studentId)))
    .orderBy(desc(lessons.startTime));
}

export async function getLessonForActor(actor: Actor, lessonId: number) {
  const db = getDb();
  const [lesson] = await db
    .select()
    .from(lessons)
    .where(and(lessonScope(actor), eq(lessons.id, lessonId)))
    .limit(1);
  return lesson ?? null;
}

/**
 * Idempotent, atomic lesson completion (Constitution Principle III business path).
 * The `ne(status, 'completed')` guard makes the UPDATE a no-op on retry — no
 * explicit transaction/row-lock needed, a single conditional UPDATE...RETURNING
 * is race-safe on its own.
 */
export async function markLessonCompleted(actor: Actor, lessonId: number, note: string) {
  const db = getDb();

  const [updated] = await db
    .update(lessons)
    .set({ status: "completed", notes: note || "" })
    .where(and(lessonScope(actor), eq(lessons.id, lessonId), ne(lessons.status, "completed")))
    .returning();

  if (!updated) {
    return getLessonForActor(actor, lessonId); // already completed (or not visible) — no-op
  }

  if (updated.packageId) {
    // Guarded by lessonsRemaining > 0 so a race or a data anomaly can never
    // push it negative — matches the DB CheckConstraint as a second line of defense.
    await db
      .update(packages)
      .set({ lessonsRemaining: sql`${packages.lessonsRemaining} - 1` })
      .where(and(eq(packages.id, updated.packageId), gt(packages.lessonsRemaining, 0)));
  }

  return updated;
}

export async function cancelLesson(actor: Actor, lessonId: number, status: "cancelled" | "no_show") {
  const db = getDb();
  const [updated] = await db
    .update(lessons)
    .set({ status })
    .where(and(lessonScope(actor), eq(lessons.id, lessonId), ne(lessons.status, "completed")))
    .returning();
  return updated ?? getLessonForActor(actor, lessonId);
}
