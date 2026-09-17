import { and, eq } from "drizzle-orm";

import { getDb } from "../db";
import { payments, students } from "../db/schema";
import type { Actor } from "../rbac";
import { paymentScope, studentScope } from "../rbac";
import { listUpcomingLessons, listWeekLessons } from "./lessons";
import { getActivePackageForStudent, packageIsLow } from "./packages";

export async function getDashboard(actor: Actor) {
  const db = getDb();

  const [week, upcoming, activeStudents, pendingPayments] = await Promise.all([
    listWeekLessons(actor),
    listUpcomingLessons(actor),
    db
      .select()
      .from(students)
      .where(and(studentScope(actor), eq(students.isActive, true))),
    db
      .select()
      .from(payments)
      .where(and(paymentScope(actor), eq(payments.status, "pending"))),
  ]);

  const lowPackageStudents = (
    await Promise.all(
      activeStudents.map(async (s) => {
        const pkg = await getActivePackageForStudent(s.id);
        return pkg && packageIsLow(pkg) ? { id: s.id, fullName: `${s.firstName} ${s.lastName}` } : null;
      }),
    )
  ).filter((s): s is { id: number; fullName: string } => s !== null);

  return {
    week,
    upcoming,
    pendingPaymentsCount: pendingPayments.length,
    activeStudentsCount: activeStudents.length,
    lowPackageStudents,
  };
}
