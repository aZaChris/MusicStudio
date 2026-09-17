import { NextResponse } from "next/server";

import { requireActor } from "@/lib/api-helpers";
import { listUpcomingLessons } from "@/lib/services/lessons";

export async function GET() {
  const { actor, error } = await requireActor();
  if (error) return error;

  const lessons = await listUpcomingLessons(actor);
  return NextResponse.json({ results: lessons });
}
