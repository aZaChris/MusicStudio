import { NextResponse } from "next/server";

import { requireActor, requireWriteRole } from "@/lib/api-helpers";
import { createPackage, listPackagesForActor } from "@/lib/services/packages";

export async function GET(request: Request) {
  const { actor, error } = await requireActor(request);
  if (error) return error;

  const { searchParams } = new URL(request.url);
  const studentId = searchParams.get("student");

  const results = await listPackagesForActor(actor, studentId ? Number(studentId) : undefined);
  return NextResponse.json({ results });
}

export async function POST(request: Request) {
  const { actor, error } = await requireActor(request);
  if (error) return error;
  if (!requireWriteRole(actor.role)) {
    return NextResponse.json({ detail: "Forbidden" }, { status: 403 });
  }

  const body = await request.json();
  const created = await createPackage({
    studentId: body.student,
    totalLessons: body.total_lessons,
    purchaseDate: body.purchase_date,
    expiryDate: body.expiry_date ?? null,
    price: body.price,
  });
  return NextResponse.json(created, { status: 201 });
}
