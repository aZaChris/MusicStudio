import { NextResponse } from "next/server";

import { requireActor } from "@/lib/api-helpers";
import { listUpcomingLessons } from "@/lib/services/lessons";

export async function GET(request: Request) {
  const { actor, error } = await requireActor(request);
  if (error) return error;

  const lessons = await listUpcomingLessons(actor);
  return NextResponse.json({ results: lessons });
}
