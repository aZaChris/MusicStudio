import { beforeEach, describe, expect, it } from "vitest";

import type { Actor } from "@/lib/rbac";
import { cancelLesson, markLessonCompleted } from "@/lib/services/lessons";
import { getDb } from "@/lib/db";
import { lessons, packages } from "@/lib/db/schema";
import { eq } from "drizzle-orm";
import { createLesson, createPackage, createStudent, createTeacher, resetDb } from "./helpers";

function teacherActor(teacherId: number): Actor {
  return { userId: 0, role: "teacher", teacherId, studioId: null, parentAccountId: null };
}

beforeEach(async () => {
  await resetDb();
});

describe("markLessonCompleted", () => {
  it("decrements the package exactly once", async () => {
    const teacher = await createTeacher();
    const student = await createStudent(teacher.id);
    const pkg = await createPackage(student.id, { totalLessons: 8, lessonsRemaining: 8 });
    const lesson = await createLesson(student.id, teacher.id, { packageId: pkg.id });

    await markLessonCompleted(teacherActor(teacher.id), lesson.id, "Great progress");

    const db = getDb();
    const [updatedPkg] = await db.select().from(packages).where(eq(packages.id, pkg.id));
    const [updatedLesson] = await db.select().from(lessons).where(eq(lessons.id, lesson.id));

    expect(updatedPkg.lessonsRemaining).toBe(7);
    expect(updatedLesson.status).toBe("completed");
    expect(updatedLesson.notes).toBe("Great progress");
  });

  it("is idempotent on retry", async () => {
    const teacher = await createTeacher();
    const student = await createStudent(teacher.id);
    const pkg = await createPackage(student.id, { totalLessons: 8, lessonsRemaining: 8 });
    const lesson = await createLesson(student.id, teacher.id, { packageId: pkg.id });

    const actor = teacherActor(teacher.id);
    await markLessonCompleted(actor, lesson.id, "");
    await markLessonCompleted(actor, lesson.id, "");
    await markLessonCompleted(actor, lesson.id, "");

    const db = getDb();
    const [updatedPkg] = await db.select().from(packages).where(eq(packages.id, pkg.id));
    expect(updatedPkg.lessonsRemaining).toBe(7);
  });

  it("never goes negative", async () => {
    const teacher = await createTeacher();
    const student = await createStudent(teacher.id);
    const pkg = await createPackage(student.id, { totalLessons: 8, lessonsRemaining: 0 });
    const lesson = await createLesson(student.id, teacher.id, { packageId: pkg.id });

    await markLessonCompleted(teacherActor(teacher.id), lesson.id, "");

    const db = getDb();
    const [updatedPkg] = await db.select().from(packages).where(eq(packages.id, pkg.id));
    expect(updatedPkg.lessonsRemaining).toBe(0);
  });

  it("does not error when the lesson has no package", async () => {
    const teacher = await createTeacher();
    const student = await createStudent(teacher.id);
    const lesson = await createLesson(student.id, teacher.id, { packageId: null });

    await markLessonCompleted(teacherActor(teacher.id), lesson.id, "");

    const db = getDb();
    const [updatedLesson] = await db.select().from(lessons).where(eq(lessons.id, lesson.id));
    expect(updatedLesson.status).toBe("completed");
  });
});

describe("cancelLesson", () => {
  it.each(["cancelled", "no_show"] as const)("%s does not decrement the package", async (status) => {
    const teacher = await createTeacher();
    const student = await createStudent(teacher.id);
    const pkg = await createPackage(student.id, { totalLessons: 8, lessonsRemaining: 8 });
    const lesson = await createLesson(student.id, teacher.id, { packageId: pkg.id });

    await cancelLesson(teacherActor(teacher.id), lesson.id, status);

    const db = getDb();
    const [updatedPkg] = await db.select().from(packages).where(eq(packages.id, pkg.id));
    const [updatedLesson] = await db.select().from(lessons).where(eq(lessons.id, lesson.id));
    expect(updatedPkg.lessonsRemaining).toBe(8);
    expect(updatedLesson.status).toBe(status);
  });
});
