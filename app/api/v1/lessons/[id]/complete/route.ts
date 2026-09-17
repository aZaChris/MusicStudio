import { NextResponse } from "next/server";

import { requireActor, requireWriteRole } from "@/lib/api-helpers";
import { markLessonCompleted } from "@/lib/services/lessons";

export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { actor, error } = await requireActor();
  if (error) return error;
  if (!requireWriteRole(actor.role)) {
    return NextResponse.json({ detail: "Forbidden" }, { status: 403 });
  }

  const { id } = await params;
  const body = await request.json().catch(() => ({}));
  const note = typeof body?.note === "string" ? body.note : "";

  const lesson = await markLessonCompleted(actor, Number(id), note);
  if (!lesson) return NextResponse.json({ detail: "Not found" }, { status: 404 });

  return NextResponse.json(lesson);
}
