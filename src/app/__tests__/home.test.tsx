import { fireEvent, screen, waitFor } from "@testing-library/react-native";

import { dashboard, lesson } from "@/test/fixtures";
import { renderApp, signedInAs, teacherMe } from "@/test/render";

test("shows the server's counts, upcoming lessons and low-package warning", async () => {
  await signedInAs(teacherMe, { "GET /dashboard/": { status: 200, body: dashboard() } });
  await renderApp("/home");

  expect(await screen.findByText("12")).toBeOnTheScreen();
  expect(screen.getByText("2")).toBeOnTheScreen();
  expect(screen.getByText("Giulia Rossi")).toBeOnTheScreen();
  expect(screen.getByText(/Giulia Rossi — Running low/)).toBeOnTheScreen();
});

test("an empty agenda says so", async () => {
  await signedInAs(teacherMe, {
    "GET /dashboard/": { status: 200, body: dashboard({ upcoming: [], low_package_students: [] }) },
  });
  await renderApp("/home");

  expect(await screen.findByText("No upcoming lessons.")).toBeOnTheScreen();
});

test("a server failure is shown with a retry, and retry recovers", async () => {
  let fail = true;
  const api = await signedInAs(teacherMe, {
    "GET /dashboard/": () => (fail ? { status: 503 } : { status: 200, body: dashboard() }),
  });
  await renderApp("/home");

  // 5xx is retried twice by policy, then shown.
  expect(await screen.findByText(/server had a problem/, {}, { timeout: 10000 })).toBeOnTheScreen();
  fail = false;
  await fireEvent.press(screen.getByRole("button", { name: "Try again" }));
  expect(await screen.findByText("12")).toBeOnTheScreen();
  expect(api.callsTo("GET /dashboard/").length).toBeGreaterThanOrEqual(4);
}, 20000);

test("a 403 is shown at once, without retries", async () => {
  const api = await signedInAs(teacherMe, { "GET /dashboard/": { status: 403, body: { detail: "No." } } });
  await renderApp("/home");

  expect(await screen.findByText("You are not allowed to do this.")).toBeOnTheScreen();
  expect(api.callsTo("GET /dashboard/")).toHaveLength(1);
});

test("completing a lesson posts the note and refreshes the home", async () => {
  let completed = false;
  const api = await signedInAs(teacherMe, {
    "GET /dashboard/": () => ({
      status: 200,
      body: dashboard({ upcoming: completed ? [] : [lesson()] }),
    }),
    "POST /lessons/1/complete/": () => {
      completed = true;
      return { status: 200, body: lesson({ status: "completed" }) };
    },
  });
  await renderApp("/home");

  await fireEvent.press(await screen.findByRole("button", { name: /Giulia Rossi/ }));
  await fireEvent.changeText(screen.getByLabelText("Progress note"), "Scales in G");
  await fireEvent.press(screen.getByRole("button", { name: "Complete" }));

  expect(await screen.findByText("No upcoming lessons.")).toBeOnTheScreen();
  expect(api.callsTo("POST /lessons/1/complete/")[0].body).toEqual({ note: "Scales in G" });
});

test("a refused completion keeps the dialog open with the server's reason", async () => {
  await signedInAs(teacherMe, {
    "GET /dashboard/": { status: 200, body: dashboard() },
    "POST /lessons/1/complete/": { status: 409, body: { detail: "Lesson already completed.", code: "conflict" } },
  });
  await renderApp("/home");

  await fireEvent.press(await screen.findByRole("button", { name: /Giulia Rossi/ }));
  await fireEvent.press(screen.getByRole("button", { name: "Complete" }));

  expect(await screen.findByText("The server rejected the request: Lesson already completed.")).toBeOnTheScreen();
  await waitFor(() => expect(screen.getByRole("button", { name: "Complete" })).toBeOnTheScreen());
});
