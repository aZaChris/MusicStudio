import { and, desc, eq, gt } from "drizzle-orm";

import { getDb } from "../db";
import { packages } from "../db/schema";
import type { Actor } from "../rbac";
import { packageScope } from "../rbac";

const LOW_THRESHOLD = 2;

export type PackageRow = typeof packages.$inferSelect;

export function packageStatus(pkg: PackageRow): "active" | "expired" | "completed" {
  if (pkg.expiryDate && new Date(pkg.expiryDate) < new Date()) return "expired";
  if (pkg.lessonsRemaining === 0) return "completed";
  return "active";
}

export function packageIsLow(pkg: PackageRow): boolean {
  return pkg.lessonsRemaining > 0 && pkg.lessonsRemaining <= LOW_THRESHOLD;
}

export async function getActivePackageForStudent(studentId: number) {
  const db = getDb();
  const [pkg] = await db
    .select()
    .from(packages)
    .where(and(eq(packages.studentId, studentId), gt(packages.lessonsRemaining, 0)))
    .orderBy(desc(packages.purchaseDate))
    .limit(1);
  return pkg ?? null;
}

export async function listPackagesForActor(actor: Actor, studentId?: number) {
  const db = getDb();
  const conditions = [packageScope(actor)];
  if (studentId) conditions.push(eq(packages.studentId, studentId));
  return db
    .select()
    .from(packages)
    .where(and(...conditions))
    .orderBy(desc(packages.purchaseDate));
}

export async function createPackage(input: {
  studentId: number;
  totalLessons: number;
  purchaseDate: string;
  expiryDate?: string | null;
  price: string;
}) {
  const db = getDb();
  const [created] = await db
    .insert(packages)
    .values({
      studentId: input.studentId,
      totalLessons: input.totalLessons,
      lessonsRemaining: input.totalLessons,
      purchaseDate: input.purchaseDate,
      expiryDate: input.expiryDate ?? null,
      price: input.price,
    })
    .returning();
  return created;
}
