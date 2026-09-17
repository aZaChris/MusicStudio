import { hash } from "bcryptjs";

import { getDb } from "@/lib/db";
import {
  lessons,
  packages,
  parentAccounts,
  parentStudentLinks,
  students,
  studios,
  teachers,
  users,
} from "@/lib/db/schema";

let seq = 0;
function nextSeq() {
  seq += 1;
  return seq;
}

export async function resetDb() {
  const db = getDb();
  // Order matters: children before parents (FK constraints).
  await db.delete(parentStudentLinks);
  await db.delete(lessons);
  await db.delete(packages);
  await db.delete(students);
  await db.delete(parentAccounts);
  await db.delete(teachers);
  await db.delete(studios);
  await db.delete(users);
}

export async function createUser(role: "teacher" | "studio_owner" | "parent") {
  const db = getDb();
  const n = nextSeq();
  const [user] = await db
    .insert(users)
    .values({
      email: `user${n}@example.com`,
      passwordHash: await hash("password123", 4),
      role,
    })
    .returning();
  return user;
}

export async function createTeacher(opts: { studioId?: number | null; isOwner?: boolean } = {}) {
  const db = getDb();
  const user = await createUser(opts.isOwner ? "studio_owner" : "teacher");
  const [teacher] = await db
    .insert(teachers)
    .values({ userId: user.id, studioId: opts.studioId ?? null, isOwner: opts.isOwner ?? false })
    .returning();
  return { ...teacher, user };
}

export async function createStudio() {
  const db = getDb();
  const n = nextSeq();
  const [studio] = await db.insert(studios).values({ name: `Studio ${n}` }).returning();
  return studio;
}

export async function createStudent(teacherId: number) {
  const db = getDb();
  const n = nextSeq();
  const [student] = await db
    .insert(students)
    .values({ firstName: `Student${n}`, lastName: "Test", instrument: "Piano", teacherId })
    .returning();
  return student;
}

export async function createPackage(
  studentId: number,
  opts: { totalLessons?: number; lessonsRemaining?: number } = {},
) {
  const db = getDb();
  const total = opts.totalLessons ?? 8;
  const [pkg] = await db
    .insert(packages)
    .values({
      studentId,
      totalLessons: total,
      lessonsRemaining: opts.lessonsRemaining ?? total,
      purchaseDate: new Date().toISOString().slice(0, 10),
      price: "120.00",
    })
    .returning();
  return pkg;
}

export async function createLesson(
  studentId: number,
  teacherId: number,
  opts: { packageId?: number | null; startTime?: Date; status?: string } = {},
) {
  const db = getDb();
  const [lesson] = await db
    .insert(lessons)
    .values({
      studentId,
      teacherId,
      packageId: opts.packageId ?? null,
      startTime: opts.startTime ?? new Date(Date.now() + 60 * 60 * 1000),
      status: (opts.status as never) ?? "scheduled",
    })
    .returning();
  return lesson;
}

export async function createParentAccount() {
  const db = getDb();
  const user = await createUser("parent");
  const [parent] = await db.insert(parentAccounts).values({ userId: user.id }).returning();
  return { ...parent, user };
}

export async function linkParentToStudent(parentAccountId: number, studentId: number) {
  const db = getDb();
  await db.insert(parentStudentLinks).values({ parentAccountId, studentId });
}
