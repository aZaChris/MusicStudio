// Startup verification, expired sessions and logout (US1).
import { fireEvent, screen, waitFor } from "@testing-library/react-native";
import * as SecureStore from "expo-secure-store";

import { session } from "@/lib/api/client";
import { dashboard } from "@/test/fixtures";
import { parentMe, renderApp, signedInAs, teacherMe } from "@/test/render";

test("startup re-verifies the stored session and routes by the server's role", async () => {
  const api = await signedInAs(parentMe, {
    "GET /students/": { status: 200, body: { count: 0, next: null, previous: null, results: [] } },
  });
  await renderApp("/");

  expect(await screen.findByText("No students are linked to your account yet.")).toBeOnTheScreen();
  expect(api.callsTo("GET /auth/me/")).toHaveLength(1);
});

test("a stored session that the server cannot confirm (offline) is kept, not signed out", async () => {
  await session.start({ access: "a", refresh: "refresh-1" });
  globalThis.fetch = jest.fn(async () => {
    throw new TypeError("Network request failed");
  }) as typeof fetch;
  await renderApp("/");

  expect(await screen.findByText("Cannot reach the server to check your account.")).toBeOnTheScreen();
  expect(await session.refreshToken()).toBe("refresh-1");
});

test("when the session cannot be renewed the user is sent to login with an explanation", async () => {
  await signedInAs(teacherMe, {
    "GET /dashboard/": { status: 401 },
    "POST /auth/token/refresh/": { status: 401, body: { detail: "Token is blacklisted" } },
  });
  await renderApp("/");

  expect(await screen.findByText("Your session has ended. Please log in again.")).toBeOnTheScreen();
  expect(await session.refreshToken()).toBeNull();
});

test("logout ends the session on the server, then locally", async () => {
  const api = await signedInAs(teacherMe, {
    "GET /dashboard/": { status: 200, body: dashboard() },
    "POST /auth/logout/": { status: 205 },
  });
  await renderApp("/");

  await fireEvent.press(await screen.findByRole("button", { name: "Log out" }));

  expect(await screen.findByLabelText("Email")).toBeOnTheScreen();
  expect(api.callsTo("POST /auth/logout/")[0].body).toEqual({ refresh: "refresh-1" });
  expect(await SecureStore.getItemAsync("musicstudio.refresh")).toBeNull();
});

test("logout with an expired access token sends the rotated refresh token, not the stale one", async () => {
  // The first logout call refreshes (rotating refresh-1 -> refresh-2) but its body still holds
  // refresh-1, which the server has just blacklisted: 400. The retry must send refresh-2.
  const api = await signedInAs(teacherMe, {
    "GET /dashboard/": { status: 200, body: dashboard() },
    "POST /auth/token/refresh/": { status: 200, body: { access: "access-2", refresh: "refresh-2" } },
    "POST /auth/logout/": (req) => {
      if (req.authorization !== "Bearer access-2") return { status: 401 };
      return (req.body as { refresh: string }).refresh === "refresh-2"
        ? { status: 205 }
        : { status: 400, body: { refresh: ["Token is blacklisted"] } };
    },
  });
  await renderApp("/");
  await screen.findByRole("button", { name: "Log out" });
  await session.start({ access: "expired", refresh: "refresh-1" }); // access expires meanwhile

  await fireEvent.press(screen.getByRole("button", { name: "Log out" }));

  await waitFor(() =>
    expect(api.callsTo("POST /auth/logout/").map((c) => (c.body as { refresh: string }).refresh)).toContain(
      "refresh-2",
    ),
  );
  expect(await screen.findByLabelText("Email")).toBeOnTheScreen();
});

test("logout still signs out locally when the server is unreachable", async () => {
  await signedInAs(teacherMe, { "GET /dashboard/": { status: 200, body: dashboard() } });
  await renderApp("/");
  await screen.findByRole("button", { name: "Log out" });
  globalThis.fetch = jest.fn(async () => {
    throw new TypeError("Network request failed");
  }) as typeof fetch;

  await fireEvent.press(screen.getByRole("button", { name: "Log out" }));

  expect(await screen.findByLabelText("Email")).toBeOnTheScreen();
  expect(await session.refreshToken()).toBeNull();
});

test("after logout and a new sign-in, nothing of the previous user is shown", async () => {
  const api = await signedInAs(teacherMe, {
    "GET /dashboard/": { status: 200, body: dashboard({ active_students_count: 12 }) },
    "POST /auth/logout/": { status: 205 },
  });
  await renderApp("/");
  expect(await screen.findByText("12")).toBeOnTheScreen();
  await fireEvent.press(screen.getByRole("button", { name: "Log out" }));
  await screen.findByLabelText("Email");

  let releaseDashboard: () => void = () => undefined;
  api.route({
    "POST /auth/token/": { status: 200, body: { access: "b", refresh: "r2" } },
    "GET /auth/me/": { status: 200, body: { ...teacherMe, id: 9, email: "luca@example.com" } },
    "GET /dashboard/": () =>
      new Promise((resolve) => {
        releaseDashboard = () => resolve({ status: 200, body: dashboard({ active_students_count: 4 }) });
      }),
  });
  await fireEvent.changeText(screen.getByLabelText("Email"), "luca@example.com");
  await fireEvent.changeText(screen.getByLabelText("Password"), "pw");
  await fireEvent.press(screen.getByRole("button", { name: "Log in" }));

  // While the new user's dashboard is still loading, the old "12" must not appear.
  expect(await screen.findByText("Hi, luca 👋")).toBeOnTheScreen();
  expect(screen.queryByText("12")).toBeNull();
  releaseDashboard();
  expect(await screen.findByText("4")).toBeOnTheScreen();
});
