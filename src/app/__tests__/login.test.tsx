import { fireEvent, screen, waitFor } from "@testing-library/react-native";

import { installFakeApi } from "@/test/fake-api";
import { renderApp, teacherMe } from "@/test/render";

test("without a session the app opens on the login screen", async () => {
  installFakeApi();
  await renderApp("/");
  expect(await screen.findByLabelText("Email")).toBeOnTheScreen();
});

test("wrong credentials show a message and store nothing", async () => {
  const api = installFakeApi({
    "POST /auth/token/": { status: 401, body: { detail: "No active account found with the given credentials" } },
  });
  await renderApp("/login");

  await fireEvent.changeText(await screen.findByLabelText("Email"), "mario.rossi@example.com");
  await fireEvent.changeText(screen.getByLabelText("Password"), "wrong");
  await fireEvent.press(screen.getByRole("button", { name: "Log in" }));

  expect(await screen.findByText("Invalid email or password.")).toBeOnTheScreen();
  expect(api.callsTo("GET /auth/me/")).toHaveLength(0);
});

test("a teacher signs in and lands on the teacher home", async () => {
  const api = installFakeApi({
    "POST /auth/token/": { status: 200, body: { access: "a", refresh: "r" } },
    "GET /auth/me/": { status: 200, body: teacherMe },
    "GET /dashboard/": {
      status: 200,
      body: { week: [], upcoming: [], pending_payments_count: 0, active_students_count: 3, low_package_students: [] },
    },
  });
  await renderApp("/login");

  await fireEvent.changeText(await screen.findByLabelText("Email"), "mario.rossi@example.com");
  await fireEvent.changeText(screen.getByLabelText("Password"), "password123");
  await fireEvent.press(screen.getByRole("button", { name: "Log in" }));

  expect(await screen.findByText("Hi, mario.rossi")).toBeOnTheScreen();
  expect(api.callsTo("POST /auth/token/")[0].body).toEqual({
    email: "mario.rossi@example.com",
    password: "password123",
  });
  await waitFor(() => expect(screen.getByText("3")).toBeOnTheScreen());
});

test("an unreachable server at login says so instead of 'invalid credentials'", async () => {
  installFakeApi();
  globalThis.fetch = jest.fn(async () => {
    throw new TypeError("Network request failed");
  }) as typeof fetch;
  await renderApp("/login");

  await fireEvent.changeText(await screen.findByLabelText("Email"), "a@b.c");
  await fireEvent.changeText(screen.getByLabelText("Password"), "x");
  await fireEvent.press(screen.getByRole("button", { name: "Log in" }));

  expect(await screen.findByText(/Cannot reach the server/)).toBeOnTheScreen();
});
