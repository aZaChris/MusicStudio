// Render the real app (src/app, real layouts and providers) at a URL. Only fetch is fake.
import { renderRouter } from "expo-router/testing-library";

import { session } from "@/lib/api/client";
import type { Me } from "@/lib/api/types";
import { installFakeApi, type FakeApi } from "./fake-api";

export async function renderApp(initialUrl: string) {
  // RNTL 14's render is async: `screen` is only bound once it resolves.
  return await renderRouter("./src/app", { initialUrl });
}

export const teacherMe: Me = {
  id: 1,
  email: "mario.rossi@example.com",
  role: "teacher",
  preferred_language: "en",
  teacher: { id: 10, studio: 100, is_owner: false },
  parent_account: null,
  email_verified: true,
  mfa_enabled: false,
};

export const parentMe: Me = {
  id: 2,
  email: "anna@example.com",
  role: "parent",
  preferred_language: "en",
  teacher: null,
  parent_account: { id: 20 },
  email_verified: true,
  mfa_enabled: false,
};

export const studentMe: Me = {
  id: 4,
  email: "luca@example.com",
  role: "student",
  preferred_language: "en",
  teacher: null,
  parent_account: null,
  email_verified: true,
  mfa_enabled: false,
};

export const ownerMe: Me = { ...teacherMe, id: 3, email: "titolare@example.com", role: "studio_owner", teacher: { id: 11, studio: 100, is_owner: true } };

/** A stored session that the startup check (/auth/me/) confirms as `me`. */
export async function signedInAs(me: Me, routes: Parameters<typeof installFakeApi>[0] = {}): Promise<FakeApi> {
  await session.start({ access: "access-1", refresh: "refresh-1" });
  return installFakeApi({ "GET /auth/me/": { status: 200, body: me }, ...routes });
}
