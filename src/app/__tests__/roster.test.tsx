import { fireEvent, screen } from "@testing-library/react-native";

import { page } from "@/test/fake-api";
import { lesson, student } from "@/test/fixtures";
import { renderApp, signedInAs, teacherMe } from "@/test/render";

const first25 = Array.from({ length: 25 }, (_, i) => student(i + 1));
const last5 = Array.from({ length: 5 }, (_, i) => student(i + 26));

test("every active student is listed, beyond the first server page", async () => {
  const api = await signedInAs(teacherMe, {
    "GET /students/?is_active=true": {
      status: 200,
      body: page(first25, "http://testserver/api/v1/students/?is_active=true&page=2"),
    },
    "GET /students/?is_active=true&page=2": { status: 200, body: page(last5) },
  });
  await renderApp("/roster");

  expect(await screen.findByText("Student1 Test")).toBeOnTheScreen();
  expect(api.callsTo("GET /students/?is_active=true&page=2")).toHaveLength(1);
  // FlatList renders lazily: give it a viewport, scroll to the end like a user, and the 30th
  // student appears.
  const list = screen.getByTestId("roster-list");
  await fireEvent(list, "layout", { nativeEvent: { layout: { x: 0, y: 0, width: 400, height: 800 } } });
  await fireEvent(list, "contentSizeChange", 400, 5000);
  await fireEvent.scroll(list, {
    nativeEvent: {
      contentOffset: { x: 0, y: 5000 },
      contentSize: { width: 400, height: 5000 },
      layoutMeasurement: { width: 400, height: 800 },
    },
  });
  expect(await screen.findByText("Student30 Test")).toBeOnTheScreen();
});

test("no students: an empty message, not a blank screen", async () => {
  await signedInAs(teacherMe, { "GET /students/": { status: 200, body: page([]) } });
  await renderApp("/roster");

  expect(await screen.findByText("No active students.")).toBeOnTheScreen();
});

test("student detail shows the package and the translated lesson history", async () => {
  await signedInAs(teacherMe, {
    "GET /students/": { status: 200, body: page([student(7)]) },
    "GET /students/7/": { status: 200, body: student(7) },
    "GET /students/7/lessons/": {
      status: 200,
      body: [lesson({ id: 1, status: "completed", notes: "Good tempo" }), lesson({ id: 2, status: "no_show" })],
    },
  });
  await renderApp("/roster");
  await fireEvent.press(await screen.findByRole("button", { name: "Student7 Test" }));

  expect(await screen.findByText("2 remaining")).toBeOnTheScreen();
  expect(screen.getByText("Active")).toBeOnTheScreen();
  expect(screen.getByText("Completed")).toBeOnTheScreen();
  expect(screen.getByText("No-show")).toBeOnTheScreen();
  expect(screen.getByText("Good tempo")).toBeOnTheScreen();
});

test("a student without an active package says so (active_package is null)", async () => {
  await signedInAs(teacherMe, {
    "GET /students/9/": { status: 200, body: student(9, { active_package: null }) },
    "GET /students/9/lessons/": { status: 200, body: [] },
  });
  await renderApp("/roster/9");

  expect(await screen.findByText("No active package")).toBeOnTheScreen();
  expect(screen.getByText("No lessons yet.")).toBeOnTheScreen();
});

test("a student that is not visible shows 'not found'", async () => {
  await signedInAs(teacherMe, {
    "GET /students/404/": { status: 404, body: { detail: "No Student matches the given query." } },
    "GET /students/404/lessons/": { status: 404, body: { detail: "Not found." } },
  });
  await renderApp("/roster/404");

  expect(await screen.findByText(/Not found\. It may have been removed/)).toBeOnTheScreen();
});
