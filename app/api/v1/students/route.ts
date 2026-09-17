import { NextResponse } from "next/server";

import { requireActor, requireWriteRole } from "@/lib/api-helpers";
import { createStudentForTeacher, listStudentsForActor } from "@/lib/services/students";

export async function GET(request: Request) {
  const { actor, error } = await requireActor();
  if (error) return error;

  const { searchParams } = new URL(request.url);
  const activeOnly = searchParams.get("is_active") !== "false";

  const results = await listStudentsForActor(actor, activeOnly);
  return NextResponse.json({ results, count: results.length });
}

export async function POST(request: Request) {
  const { actor, error } = await requireActor();
  if (error) return error;
  if (!requireWriteRole(actor.role) || !actor.teacherId) {
    return NextResponse.json({ detail: "Forbidden" }, { status: 403 });
  }

  const body = await request.json();
  const created = await createStudentForTeacher({
    teacherId: actor.teacherId,
    firstName: body.first_name,
    lastName: body.last_name,
    instrument: body.instrument,
  });
  return NextResponse.json(created, { status: 201 });
}
