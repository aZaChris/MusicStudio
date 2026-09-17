/**
 * Constitution Principle I (Tenant Isolation & RBAC) choke point.
 *
 * Every service function touching Student/Lesson/Package/Payment data MUST
 * scope its query through one of the `*Scope()` builders below (SQL-level
 * filtering) rather than relying on UI-level hiding. A caller outside their
 * scope gets "not found", never a 200 with someone else's data.
 */
import { eq, inArray, sql, type SQL } from "drizzle-orm";

import { getDb } from "./db";
import {
  lessons,
  packages,
  parentAccounts,
  parentStudentLinks,
  payments,
  students,
  teachers,
} from "./db/schema";
import type { Role } from "./auth";

export interface Actor {
  userId: number;
  role: Role;
  teacherId: number | null;
  studioId: number | null;
  parentAccountId: number | null;
}

const NONE: SQL = sql`false`;

export async function getActor(userId: number, role: Role): Promise<Actor> {
  const db = getDb();

  if (role === "teacher" || role === "studio_owner") {
    const [teacher] = await db.select().from(teachers).where(eq(teachers.userId, userId)).limit(1);
    return {
      userId,
      role,
      teacherId: teacher?.id ?? null,
      studioId: teacher?.studioId ?? null,
      parentAccountId: null,
    };
  }

  const [parentAccount] = await db
    .select()
    .from(parentAccounts)
    .where(eq(parentAccounts.userId, userId))
    .limit(1);

  return {
    userId,
    role,
    teacherId: null,
    studioId: null,
    parentAccountId: parentAccount?.id ?? null,
  };
}

function linkedStudentIds(actor: Actor) {
  const db = getDb();
  return db
    .select({ id: parentStudentLinks.studentId })
    .from(parentStudentLinks)
    .where(eq(parentStudentLinks.parentAccountId, actor.parentAccountId!));
}

function studioTeacherIds(actor: Actor) {
  const db = getDb();
  return db.select({ id: teachers.id }).from(teachers).where(eq(teachers.studioId, actor.studioId!));
}

export function studentScope(actor: Actor): SQL {
  if (actor.role === "teacher") {
    return actor.teacherId ? eq(students.teacherId, actor.teacherId) : NONE;
  }
  if (actor.role === "studio_owner") {
    return actor.studioId ? inArray(students.teacherId, studioTeacherIds(actor)) : NONE;
  }
  return actor.parentAccountId ? inArray(students.id, linkedStudentIds(actor)) : NONE;
}

export function lessonScope(actor: Actor): SQL {
  if (actor.role === "teacher") {
    return actor.teacherId ? eq(lessons.teacherId, actor.teacherId) : NONE;
  }
  if (actor.role === "studio_owner") {
    return actor.studioId ? inArray(lessons.teacherId, studioTeacherIds(actor)) : NONE;
  }
  return actor.parentAccountId ? inArray(lessons.studentId, linkedStudentIds(actor)) : NONE;
}

export function packageScope(actor: Actor): SQL {
  if (actor.role === "teacher") {
    return actor.teacherId ? inArray(packages.studentId, studentIdsForTeacher(actor)) : NONE;
  }
  if (actor.role === "studio_owner") {
    return actor.studioId ? inArray(packages.studentId, studentIdsForStudio(actor)) : NONE;
  }
  return actor.parentAccountId ? inArray(packages.studentId, linkedStudentIds(actor)) : NONE;
}

export function paymentScope(actor: Actor): SQL {
  if (actor.role === "teacher") {
    return actor.teacherId ? inArray(payments.studentId, studentIdsForTeacher(actor)) : NONE;
  }
  if (actor.role === "studio_owner") {
    return actor.studioId ? inArray(payments.studentId, studentIdsForStudio(actor)) : NONE;
  }
  return actor.parentAccountId ? inArray(payments.studentId, linkedStudentIds(actor)) : NONE;
}

function studentIdsForTeacher(actor: Actor) {
  const db = getDb();
  return db.select({ id: students.id }).from(students).where(eq(students.teacherId, actor.teacherId!));
}

function studentIdsForStudio(actor: Actor) {
  const db = getDb();
  return db
    .select({ id: students.id })
    .from(students)
    .where(inArray(students.teacherId, studioTeacherIds(actor)));
}

export function canWrite(actor: Actor): boolean {
  return actor.role === "teacher" || actor.role === "studio_owner";
}
