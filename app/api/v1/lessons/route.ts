import { NextResponse } from "next/server";

import { requireActor } from "@/lib/api-helpers";
import { listWeekLessons } from "@/lib/services/lessons";

export async function GET(request: Request) {
  const { actor, error } = await requireActor(request);
  if (error) return error;

  const { searchParams } = new URL(request.url);
  const week = searchParams.get("week");
  const anchor = week ? new Date(week) : new Date();

  const lessons = await listWeekLessons(actor, anchor);
  return NextResponse.json({ results: lessons });
}
