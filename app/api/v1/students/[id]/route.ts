import { NextResponse } from "next/server";

import { requireActor } from "@/lib/api-helpers";
import { getStudentForActor } from "@/lib/services/students";

export async function GET(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { actor, error } = await requireActor(request);
  if (error) return error;

  const { id } = await params;
  const student = await getStudentForActor(actor, Number(id));
  if (!student) return NextResponse.json({ detail: "Not found" }, { status: 404 });

  return NextResponse.json(student);
}
