import { NextResponse } from "next/server";

import { requireActor, requireWriteRole } from "@/lib/api-helpers";
import { createPayment, listPaymentsForActor, PaymentValidationError } from "@/lib/services/payments";

export async function GET(request: Request) {
  const { actor, error } = await requireActor();
  if (error) return error;

  const { searchParams } = new URL(request.url);
  const status = searchParams.get("status") ?? undefined;

  const results = await listPaymentsForActor(actor, status);
  return NextResponse.json({ results });
}

export async function POST(request: Request) {
  const { actor, error } = await requireActor();
  if (error) return error;
  if (!requireWriteRole(actor.role)) {
    return NextResponse.json({ detail: "Forbidden" }, { status: 403 });
  }

  const body = await request.json();
  try {
    const created = await createPayment({
      studentId: body.student,
      packageId: body.package ?? null,
      amount: body.amount,
      date: body.date,
      method: body.method,
      status: body.status,
    });
    return NextResponse.json(created, { status: 201 });
  } catch (err) {
    if (err instanceof PaymentValidationError) {
      return NextResponse.json({ package: err.message }, { status: 400 });
    }
    throw err;
  }
}
