import { compare } from "bcryptjs";
import { eq } from "drizzle-orm";
import { NextResponse } from "next/server";

import { getDb } from "@/lib/db";
import { users } from "@/lib/db/schema";
import { signMobileToken } from "@/lib/mobile-auth";

/**
 * Credentials login for the React Native app — returns a Bearer token instead
 * of a session cookie (mobile clients don't share the browser's cookie jar).
 */
export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const email = body?.email as string | undefined;
  const password = body?.password as string | undefined;
  if (!email || !password) {
    return NextResponse.json({ detail: "email and password are required" }, { status: 400 });
  }

  const db = getDb();
  const [user] = await db.select().from(users).where(eq(users.email, email)).limit(1);
  if (!user || !(await compare(password, user.passwordHash))) {
    return NextResponse.json({ detail: "Invalid credentials" }, { status: 401 });
  }

  const token = signMobileToken({
    userId: user.id,
    role: user.role,
    preferredLanguage: user.preferredLanguage,
  });

  return NextResponse.json({
    token,
    user: { id: user.id, email: user.email, role: user.role, preferredLanguage: user.preferredLanguage },
  });
}
