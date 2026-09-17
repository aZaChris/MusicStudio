import jwt from "jsonwebtoken";

import type { Role } from "./auth";

export interface MobileTokenPayload {
  userId: number;
  role: Role;
  preferredLanguage: "en" | "it";
}

const EXPIRES_IN = "30d";

/**
 * Bearer-token scheme for the React Native app (Constitution Principle II: a
 * future mobile client consumes /api/v1/ without backend changes beyond what
 * any new feature needs — this is that one-time addition). Kept fully
 * separate from Auth.js's own session-cookie JWT so neither can break the
 * other: the web app is unaffected by this.
 */
export function signMobileToken(payload: MobileTokenPayload): string {
  return jwt.sign(payload, process.env.AUTH_SECRET!, { expiresIn: EXPIRES_IN });
}

export function verifyMobileToken(token: string): MobileTokenPayload | null {
  try {
    return jwt.verify(token, process.env.AUTH_SECRET!) as MobileTokenPayload;
  } catch {
    return null;
  }
}
