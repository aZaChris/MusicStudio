import { and, desc, eq } from "drizzle-orm";

import { getDb } from "../db";
import { packages, payments, students } from "../db/schema";
import type { Actor } from "../rbac";
import { paymentScope } from "../rbac";

export class PaymentValidationError extends Error {}

export async function listPaymentsForActor(actor: Actor, status?: string) {
  const db = getDb();
  const conditions = [paymentScope(actor)];
  if (status) conditions.push(eq(payments.status, status as (typeof payments.status.enumValues)[number]));

  return db
    .select({
      id: payments.id,
      studentId: payments.studentId,
      studentFirstName: students.firstName,
      studentLastName: students.lastName,
      packageId: payments.packageId,
      amount: payments.amount,
      date: payments.date,
      method: payments.method,
      status: payments.status,
    })
    .from(payments)
    .innerJoin(students, eq(payments.studentId, students.id))
    .where(and(...conditions))
    .orderBy(desc(payments.date));
}

export async function createPayment(input: {
  studentId: number;
  packageId?: number | null;
  amount: string;
  date: string;
  method: "cash" | "bank_transfer" | "manual_entry";
  status?: "paid" | "pending" | "overdue";
}) {
  const db = getDb();

  if (input.packageId) {
    const [pkg] = await db.select().from(packages).where(eq(packages.id, input.packageId)).limit(1);
    if (!pkg || pkg.studentId !== input.studentId) {
      throw new PaymentValidationError("Package must belong to the same student as the payment.");
    }
  }

  const [created] = await db
    .insert(payments)
    .values({
      studentId: input.studentId,
      packageId: input.packageId ?? null,
      amount: input.amount,
      date: input.date,
      method: input.method,
      status: input.status ?? "pending",
    })
    .returning();
  return created;
}

export async function updatePaymentStatus(
  actor: Actor,
  paymentId: number,
  status: "paid" | "pending" | "overdue",
) {
  const db = getDb();
  const [updated] = await db
    .update(payments)
    .set({ status })
    .where(and(paymentScope(actor), eq(payments.id, paymentId)))
    .returning();
  return updated ?? null;
}
