import { NextResponse } from "next/server";

import { auth } from "./auth";
import { getActor } from "./rbac";

export async function requireActor() {
  const session = await auth();
  if (!session) {
    return { error: NextResponse.json({ detail: "Unauthorized" }, { status: 401 }) } as const;
  }
  const actor = await getActor(Number(session.user.id), session.user.role);
  return { actor, session } as const;
}

export function requireWriteRole(role: string) {
  return role === "teacher" || role === "studio_owner";
}
