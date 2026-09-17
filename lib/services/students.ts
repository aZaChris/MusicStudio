import { and, desc, eq } from "drizzle-orm";

import { getDb } from "../db";
import { payments, students } from "../db/schema";
import type { Actor } from "../rbac";
import { studentScope } from "../rbac";
import { getActivePackageForStudent, packageIsLow, packageStatus } from "./packages";

async function latestPaymentStatus(studentId: number) {
  const db = getDb();
  const [payment] = await db
    .select({ status: payments.status })
    .from(payments)
    .where(eq(payments.studentId, studentId))
    .orderBy(desc(payments.date))
    .limit(1);
  return payment?.status ?? null;
}

export async function listStudentsForActor(actor: Actor, activeOnly = true) {
  const db = getDb();
  const conditions = [studentScope(actor)];
  if (activeOnly) conditions.push(eq(students.isActive, true));

  const rows = await db
    .select()
    .from(students)
    .where(and(...conditions))
    .orderBy(students.lastName, students.firstName);

  return Promise.all(
    rows.map(async (student) => {
      const activePackage = await getActivePackageForStudent(student.id);
      const paymentStatus = await latestPaymentStatus(student.id);
      return {
        ...student,
        fullName: `${student.firstName} ${student.lastName}`,
        activePackage: activePackage
          ? { ...activePackage, status: packageStatus(activePackage), isLow: packageIsLow(activePackage) }
          : null,
        paymentStatus,
      };
    }),
  );
}

export async function getStudentForActor(actor: Actor, studentId: number) {
  const db = getDb();
  const [student] = await db
    .select()
    .from(students)
    .where(and(studentScope(actor), eq(students.id, studentId)))
    .limit(1);
  if (!student) return null;

  const activePackage = await getActivePackageForStudent(student.id);
  return {
    ...student,
    fullName: `${student.firstName} ${student.lastName}`,
    activePackage: activePackage
      ? { ...activePackage, status: packageStatus(activePackage), isLow: packageIsLow(activePackage) }
      : null,
  };
}

export async function createStudentForTeacher(input: {
  teacherId: number;
  firstName: string;
  lastName: string;
  instrument: string;
}) {
  const db = getDb();
  const [created] = await db
    .insert(students)
    .values({
      teacherId: input.teacherId,
      firstName: input.firstName,
      lastName: input.lastName,
      instrument: input.instrument,
    })
    .returning();
  return created;
}
