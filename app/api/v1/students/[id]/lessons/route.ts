import { NextResponse } from "next/server";

import { requireActor } from "@/lib/api-helpers";
import { listStudentLessons } from "@/lib/services/lessons";
import { getStudentForActor } from "@/lib/services/students";

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { actor, error } = await requireActor();
  if (error) return error;

  const { id } = await params;
  const studentId = Number(id);

  const student = await getStudentForActor(actor, studentId);
  if (!student) return NextResponse.json({ detail: "Not found" }, { status: 404 });

  const results = await listStudentLessons(actor, studentId);
  return NextResponse.json(results);
}
