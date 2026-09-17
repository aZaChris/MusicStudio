import { beforeEach, describe, expect, it } from "vitest";

import { eq } from "drizzle-orm";

import { getDb } from "@/lib/db";
import { lessons } from "@/lib/db/schema";
import type { Actor } from "@/lib/rbac";
import { markLessonCompleted } from "@/lib/services/lessons";
import { listStudentsForActor } from "@/lib/services/students";
import {
  createLesson,
  createPackage,
  createParentAccount,
  createStudent,
  createStudio,
  createTeacher,
  linkParentToStudent,
  resetDb,
} from "./helpers";

function actorFor(role: Actor["role"], ids: Partial<Actor>): Actor {
  return { userId: 0, role, teacherId: null, studioId: null, parentAccountId: null, ...ids };
}

beforeEach(async () => {
  await resetDb();
});

describe("tenant isolation (Constitution Principle I)", () => {
  it("a teacher only sees their own students", async () => {
    const teacherA = await createTeacher();
    const teacherB = await createTeacher();
    const ownStudent = await createStudent(teacherA.id);
    await createStudent(teacherB.id);

    const results = await listStudentsForActor(actorFor("teacher", { teacherId: teacherA.id }));

    expect(results.map((s) => s.id)).toEqual([ownStudent.id]);
  });

  it("a studio owner sees every student across their studio, and nothing outside it", async () => {
    const studio = await createStudio();
    const owner = await createTeacher({ studioId: studio.id, isOwner: true });
    const member = await createTeacher({ studioId: studio.id });
    const studentA = await createStudent(owner.id);
    const studentB = await createStudent(member.id);
    const outsideTeacher = await createTeacher();
    await createStudent(outsideTeacher.id);

    const results = await listStudentsForActor(
      actorFor("studio_owner", { teacherId: owner.id, studioId: studio.id }),
    );

    expect(new Set(results.map((s) => s.id))).toEqual(new Set([studentA.id, studentB.id]));
  });

  it("a teacher cannot complete another teacher's lesson (scoped query is a safe no-op)", async () => {
    const outsider = await createTeacher();
    const owner = await createTeacher();
    const student = await createStudent(owner.id);
    const pkg = await createPackage(student.id, { totalLessons: 8, lessonsRemaining: 8 });
    const lesson = await createLesson(student.id, owner.id, { packageId: pkg.id });

    await markLessonCompleted(actorFor("teacher", { teacherId: outsider.id }), lesson.id, "");

    const db = getDb();
    const [untouched] = await db.select().from(lessons).where(eq(lessons.id, lesson.id));
    expect(untouched.status).toBe("scheduled"); // outsider's call never reached this row

    const completed = await markLessonCompleted(actorFor("teacher", { teacherId: owner.id }), lesson.id, "");
    expect(completed?.status).toBe("completed"); // the actual owner can complete it
  });

  it("a parent sees only their linked student(s), never another family's", async () => {
    const teacher = await createTeacher();
    const linkedStudent = await createStudent(teacher.id);
    await createStudent(teacher.id); // unrelated student, same teacher, not linked
    const parent = await createParentAccount();
    await linkParentToStudent(parent.id, linkedStudent.id);

    const results = await listStudentsForActor(actorFor("parent", { parentAccountId: parent.id }));

    expect(results.map((s) => s.id)).toEqual([linkedStudent.id]);
  });

  it("a parent linked to siblings sees only those students", async () => {
    const teacher = await createTeacher();
    const childA = await createStudent(teacher.id);
    const childB = await createStudent(teacher.id);
    const unrelated = await createStudent(teacher.id);
    const parent = await createParentAccount();
    await linkParentToStudent(parent.id, childA.id);
    await linkParentToStudent(parent.id, childB.id);

    const results = await listStudentsForActor(actorFor("parent", { parentAccountId: parent.id }));

    const ids = new Set(results.map((s) => s.id));
    expect(ids).toEqual(new Set([childA.id, childB.id]));
    expect(ids.has(unrelated.id)).toBe(false);
  });
});
