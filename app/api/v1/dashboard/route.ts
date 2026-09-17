import { NextResponse } from "next/server";

import { requireActor } from "@/lib/api-helpers";
import { getDashboard } from "@/lib/services/dashboard";

export async function GET(request: Request) {
  const { actor, error } = await requireActor(request);
  if (error) return error;

  const dashboard = await getDashboard(actor);
  return NextResponse.json(dashboard);
}
