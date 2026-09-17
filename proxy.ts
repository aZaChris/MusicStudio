import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { auth } from "@/lib/auth";

const TEACHER_ONLY_PREFIXES = ["/dashboard", "/students", "/payments"];

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const session = await auth();

  if (!session) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  const isTeacherOnly = TEACHER_ONLY_PREFIXES.some((p) => pathname.startsWith(p));
  if (isTeacherOnly && session.user.role === "parent") {
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}

export const proxyConfig = {
  matcher: ["/dashboard/:path*", "/students/:path*", "/payments/:path*", "/parent/:path*"],
};
