import { NextResponse } from "next/server";

import { requireActor, requireWriteRole } from "@/lib/api-helpers";
import { updatePaymentStatus } from "@/lib/services/payments";

export async function PATCH(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { actor, error } = await requireActor();
  if (error) return error;
  if (!requireWriteRole(actor.role)) {
    return NextResponse.json({ detail: "Forbidden" }, { status: 403 });
  }

  const { id } = await params;
  const body = await request.json();

  const updated = await updatePaymentStatus(actor, Number(id), body.status);
  if (!updated) return NextResponse.json({ detail: "Not found" }, { status: 404 });

  return NextResponse.json(updated);
}
