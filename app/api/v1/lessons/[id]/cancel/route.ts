import { NextResponse } from "next/server";

import { requireActor, requireWriteRole } from "@/lib/api-helpers";
import { cancelLesson } from "@/lib/services/lessons";

export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { actor, error } = await requireActor();
  if (error) return error;
  if (!requireWriteRole(actor.role)) {
    return NextResponse.json({ detail: "Forbidden" }, { status: 403 });
  }

  const { id } = await params;
  const body = await request.json().catch(() => ({}));
  if (body?.status !== "cancelled" && body?.status !== "no_show") {
    return NextResponse.json({ detail: "status must be 'cancelled' or 'no_show'" }, { status: 400 });
  }

  const lesson = await cancelLesson(actor, Number(id), body.status);
  if (!lesson) return NextResponse.json({ detail: "Not found" }, { status: 404 });

  return NextResponse.json(lesson);
}
