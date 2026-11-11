import { fireEvent, screen } from "@testing-library/react-native";

import { page } from "@/test/fake-api";
import { lesson, payment, student } from "@/test/fixtures";
import { parentMe, renderApp, signedInAs } from "@/test/render";

const routes = {
  "GET /students/": {
    status: 200,
    body: page([student(7, { full_name: "Giulia Rossi" }), student(8, { full_name: "Marco Rossi" })]),
  },
  "GET /students/7/lessons/": { status: 200, body: [lesson({ id: 1, status: "completed", notes: "Bravissima" })] },
  "GET /students/8/lessons/": { status: 200, body: [lesson({ id: 2, student: 8, status: "no_show" })] },
  "GET /payments/?student=7": { status: 200, body: page([payment(1, { amount: "120.00" })]) },
  "GET /payments/?student=8": { status: 200, body: page([payment(2, { student: 8, amount: "90.00", status: "overdue" })]) },
};

test("a parent with two children switches between them; payments are filtered by the server", async () => {
  const api = await signedInAs(parentMe, routes);
  await renderApp("/portal");

  expect(await screen.findByText("Bravissima")).toBeOnTheScreen();
  expect(await screen.findByText("€120.00")).toBeOnTheScreen();

  await fireEvent.press(screen.getByRole("tab", { name: "Marco Rossi" }));

  expect(await screen.findByText("No-show")).toBeOnTheScreen();
  expect(await screen.findByText("Overdue")).toBeOnTheScreen();
  expect(api.callsTo("GET /payments/").map((c) => c.path)).toEqual(["/payments/?student=7", "/payments/?student=8"]);
});

test("the portal is read-only: the only actions are privacy and logging out", async () => {
  await signedInAs(parentMe, routes);
  await renderApp("/portal");
  await screen.findByText("Bravissima");

  expect(screen.getAllByRole("button").map((b) => b.props.accessibilityLabel)).toEqual(["Privacy", "Log out"]);
});

test("a parent with no linked children sees a clear message", async () => {
  await signedInAs(parentMe, { "GET /students/": { status: 200, body: page([]) } });
  await renderApp("/portal");

  expect(await screen.findByText("No students are linked to your account yet.")).toBeOnTheScreen();
});
