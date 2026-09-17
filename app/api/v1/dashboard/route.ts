import { NextResponse } from "next/server";

import { requireActor } from "@/lib/api-helpers";
import { getDashboard } from "@/lib/services/dashboard";

export async function GET() {
  const { actor, error } = await requireActor();
  if (error) return error;

  const dashboard = await getDashboard(actor);
  return NextResponse.json(dashboard);
}
