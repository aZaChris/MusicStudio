import * as SecureStore from "expo-secure-store";

import { ApiError, apiFetch, fetchAllPages, session } from "../api/client";
import { installFakeApi, page } from "@/test/fake-api";

const tokensAfterRefresh = { access: "access-2", refresh: "refresh-2" };

async function signedIn(access = "access-1") {
  await session.start({ access, refresh: "refresh-1" });
}

test("authenticated requests carry the bearer token", async () => {
  await signedIn();
  const api = installFakeApi({ "GET /auth/me/": { status: 200, body: { id: 1 } } });

  await apiFetch("/auth/me/");

  expect(api.calls[0].authorization).toBe("Bearer access-1");
});

test("a 401 triggers one refresh, stores the rotated token and retries once", async () => {
  await signedIn("expired");
  const api = installFakeApi({
    "POST /auth/token/refresh/": { status: 200, body: tokensAfterRefresh },
    "GET /dashboard/": (req) =>
      req.authorization === "Bearer access-2" ? { status: 200, body: { ok: true } } : { status: 401 },
  });

  await expect(apiFetch("/dashboard/")).resolves.toEqual({ ok: true });

  expect(api.callsTo("POST /auth/token/refresh/")).toHaveLength(1);
  expect(api.callsTo("POST /auth/token/refresh/")[0].body).toEqual({ refresh: "refresh-1" });
  expect(await SecureStore.getItemAsync("musicstudio.refresh")).toBe("refresh-2");
});

test("three concurrent 401s share a single refresh (the backend blacklists rotated tokens)", async () => {
  await signedIn("expired");
  const api = installFakeApi({
    "POST /auth/token/refresh/": async () => {
      await new Promise((r) => setTimeout(r, 10));
      return { status: 200, body: tokensAfterRefresh };
    },
    "GET /a/": (r) => (r.authorization === "Bearer access-2" ? { status: 200, body: 1 } : { status: 401 }),
    "GET /b/": (r) => (r.authorization === "Bearer access-2" ? { status: 200, body: 2 } : { status: 401 }),
    "GET /c/": (r) => (r.authorization === "Bearer access-2" ? { status: 200, body: 3 } : { status: 401 }),
  });

  await expect(Promise.all([apiFetch("/a/"), apiFetch("/b/"), apiFetch("/c/")])).resolves.toEqual([1, 2, 3]);
  expect(api.callsTo("POST /auth/token/refresh/")).toHaveLength(1);
});

test("a refused refresh clears the session and tells the listeners", async () => {
  await signedIn("expired");
  installFakeApi({
    "POST /auth/token/refresh/": { status: 401, body: { detail: "Token is blacklisted" } },
    "GET /dashboard/": { status: 401 },
  });
  const expired = jest.fn();
  const stop = session.onExpired(expired);

  await expect(apiFetch("/dashboard/")).rejects.toMatchObject({ status: 401 });

  expect(expired).toHaveBeenCalledTimes(1);
  expect(await session.refreshToken()).toBeNull();
  stop();
});

test("no stored session: the request goes without a token and fails with 401", async () => {
  const api = installFakeApi({ "GET /dashboard/": { status: 401 } });

  await expect(apiFetch("/dashboard/")).rejects.toMatchObject({ status: 401 });
  expect(api.calls[0].authorization).toBeNull();
});

test("an unreachable server is status 0 and does not sign the user out", async () => {
  await signedIn();
  global.fetch = jest.fn(async () => {
    throw new TypeError("Network request failed");
  }) as typeof fetch;

  await expect(apiFetch("/dashboard/")).rejects.toMatchObject({ status: 0 });
  expect(await session.refreshToken()).toBe("refresh-1");
});

test("server errors keep detail, code and field errors", async () => {
  await signedIn();
  installFakeApi({
    "POST /payments/": { status: 400, body: { amount: ["A valid number is required."] } },
    "POST /lessons/1/complete/": { status: 409, body: { detail: "Already completed.", code: "conflict" } },
  });

  const fieldError = await apiFetch("/payments/", { method: "POST", body: {} }).catch((e) => e);
  expect(fieldError).toBeInstanceOf(ApiError);
  expect(fieldError.fieldErrors).toEqual({ amount: ["A valid number is required."] });

  const conflict = await apiFetch("/lessons/1/complete/", { method: "POST", body: {} }).catch((e) => e);
  expect(conflict).toMatchObject({ status: 409, detail: "Already completed.", code: "conflict" });
});

test("login does not try to refresh on 401: it means wrong credentials", async () => {
  const api = installFakeApi({ "POST /auth/token/": { status: 401, body: { detail: "No active account" } } });

  await expect(apiFetch("/auth/token/", { method: "POST", body: {}, auth: false })).rejects.toMatchObject({
    status: 401,
  });
  expect(api.callsTo("POST /auth/token/refresh/")).toHaveLength(0);
});

test("205 and 204 resolve without a body", async () => {
  await signedIn();
  installFakeApi({ "POST /auth/logout/": { status: 205 } });

  await expect(apiFetch("/auth/logout/", { method: "POST", body: { refresh: "r" } })).resolves.toBeUndefined();
});

test("fetchAllPages follows DRF next links (absolute URLs) to the end", async () => {
  await signedIn();
  const api = installFakeApi({
    "GET /students/?is_active=true": { status: 200, body: page([{ id: 1 }], "http://other-host/api/v1/students/?is_active=true&page=2") },
    "GET /students/?is_active=true&page=2": { status: 200, body: page([{ id: 2 }]) },
  });

  await expect(fetchAllPages("/students/?is_active=true")).resolves.toEqual([{ id: 1 }, { id: 2 }]);
  // The next link's host is ignored: we always talk to the configured API.
  expect(api.calls.map((c) => c.path)).toEqual(["/students/?is_active=true", "/students/?is_active=true&page=2"]);
});
