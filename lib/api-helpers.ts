import { NextResponse } from "next/server";

import { auth } from "./auth";
import { verifyMobileToken } from "./mobile-auth";
import type { Actor } from "./rbac";
import { getActor } from "./rbac";

type ActorResult =
  | { actor: Actor; error?: undefined }
  | { actor?: undefined; error: NextResponse };

function unauthorized(): ActorResult {
  return { error: NextResponse.json({ detail: "Unauthorized" }, { status: 401 }) };
}

/**
 * Two auth paths into the same API (Constitution Principle II): the web app
 * uses Auth.js's session cookie, the React Native app sends
 * `Authorization: Bearer <token>` from /api/v1/auth/login. Whichever is
 * present resolves to the same Actor the rest of the service layer uses.
 */
export async function requireActor(request: Request): Promise<ActorResult> {
  const authHeader = request.headers.get("authorization");
  if (authHeader?.startsWith("Bearer ")) {
    const payload = verifyMobileToken(authHeader.slice("Bearer ".length));
    if (!payload) return unauthorized();
    const actor = await getActor(payload.userId, payload.role);
    return { actor };
  }

  const session = await auth();
  if (!session) return unauthorized();
  const actor = await getActor(Number(session.user.id), session.user.role);
  return { actor };
}

export function requireWriteRole(role: string) {
  return role === "teacher" || role === "studio_owner";
}
