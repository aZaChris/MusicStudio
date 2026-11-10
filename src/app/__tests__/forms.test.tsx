import { fireEvent, screen, waitFor } from "@testing-library/react-native";

import { page } from "@/test/fake-api";
import { lesson, student } from "@/test/fixtures";
import { renderApp, signedInAs, teacherMe } from "@/test/render";

// Only Date is faked: Tuesday 10 Nov 2026, 09:00 in Rome.
const realTimers = ["setTimeout", "setInterval", "setImmediate", "clearTimeout", "clearInterval",
  "clearImmediate", "nextTick", "queueMicrotask", "requestAnimationFrame", "cancelAnimationFrame",
  "requestIdleCallback", "cancelIdleCallback", "hrtime", "performance"] as const;

beforeEach(() => jest.useFakeTimers({ now: new Date(2026, 10, 10, 9, 0), doNotFake: [...realTimers] }));
afterEach(() => jest.useRealTimers());

const giulia = student(7, { first_name: "Giulia", last_name: "Rossi", full_name: "Giulia Rossi" });

const detailRoutes = (more: Parameters<typeof signedInAs>[1] = {}) => ({
  "GET /students/7/": { status: 200, body: giulia },
  "GET /students/7/lessons/": { status: 200, body: [lesson({ id: 4 })] },
  ...more,
});

test("adding a student posts trimmed names and opens the new student", async () => {
  const api = await signedInAs(teacherMe, {
    "GET /students/": { status: 200, body: page([student(1)]) },
    "POST /students/": { status: 201, body: student(5, { full_name: "Anna Verdi" }) },
    "GET /students/5/": { status: 200, body: student(5, { full_name: "Anna Verdi", active_package: null }) },
    "GET /students/5/lessons/": { status: 200, body: [] },
  });
  await renderApp("/roster");

  await fireEvent.press(await screen.findByRole("button", { name: "New student" }));
  await fireEvent.changeText(await screen.findByLabelText("First name"), " Anna ");
  await fireEvent.changeText(screen.getByLabelText("Last name"), "Verdi");
  await fireEvent.changeText(screen.getByLabelText("Instrument"), "Violin");
  await fireEvent.press(screen.getByRole("button", { name: "Save" }));

  await waitFor(() => expect(api.callsTo("POST /students/")).toHaveLength(1));
  expect(api.callsTo("POST /students/")[0].body).toEqual({ first_name: "Anna", last_name: "Verdi", instrument: "Violin" });
  expect(await screen.findByText("Anna Verdi")).toBeOnTheScreen();
});

test("Save stays off until the three fields are filled", async () => {
  await signedInAs(teacherMe, { "GET /students/": { status: 200, body: page([]) } });
  await renderApp("/roster");

  await fireEvent.press(await screen.findByRole("button", { name: "New student" }));
  await fireEvent.changeText(await screen.findByLabelText("First name"), "Anna");

  expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
});

test("selling a package posts the size, the price with a point and today's date", async () => {
  const api = await signedInAs(teacherMe, detailRoutes({ "POST /packages/": { status: 201, body: { id: 9 } } }));
  await renderApp("/roster/7");

  await fireEvent.press(await screen.findByRole("button", { name: "New package" }));
  await fireEvent.press(await screen.findByRole("radio", { name: "20" }));
  await fireEvent.changeText(screen.getByLabelText("Price (€)"), "180,50");
  await fireEvent.press(screen.getByRole("radio", { name: "In 6 months" }));
  await fireEvent.press(screen.getByRole("button", { name: "Save" }));

  await waitFor(() => expect(api.callsTo("POST /packages/")).toHaveLength(1));
  expect(api.callsTo("POST /packages/")[0].body).toEqual({
    student: 7,
    total_lessons: 20,
    price: "180.50",
    purchase_date: "2026-11-10",
    expiry_date: "2027-05-10",
  });
});

test("scheduling a lesson sends the local wall-clock time", async () => {
  const api = await signedInAs(teacherMe, detailRoutes({ "POST /lessons/": { status: 201, body: lesson({ id: 5 }) } }));
  await renderApp("/roster/7");

  await fireEvent.press(await screen.findByRole("button", { name: "Schedule a lesson" }));
  await fireEvent.press(await screen.findByRole("radio", { name: "Tomorrow" }));
  await fireEvent.press(screen.getByRole("radio", { name: "16:30" }));
  await fireEvent.press(screen.getByRole("radio", { name: "60 min" }));
  await fireEvent.press(screen.getByRole("button", { name: "Save" }));

  await waitFor(() => expect(api.callsTo("POST /lessons/")).toHaveLength(1));
  const sent = api.callsTo("POST /lessons/")[0].body as { start_time: string; duration_minutes: number; student: number };
  // 16:30 in Rome on 11 Nov (UTC+1) is 15:30 UTC.
  expect(sent.start_time).toBe("2026-11-11T15:30:00.000Z");
  expect(sent).toMatchObject({ student: 7, duration_minutes: 60 });
});

test("an overlapping lesson shows the 409 reason and the sheet stays open", async () => {
  await signedInAs(
    teacherMe,
    detailRoutes({ "POST /lessons/": { status: 409, body: { detail: "Overlaps another lesson.", code: "conflict" } } }),
  );
  await renderApp("/roster/7");

  await fireEvent.press(await screen.findByRole("button", { name: "Schedule a lesson" }));
  await fireEvent.press(await screen.findByRole("button", { name: "Save" }));

  expect(await screen.findByText(/Overlaps another lesson/)).toBeOnTheScreen();
  expect(screen.getByRole("button", { name: "Save" })).toBeOnTheScreen();
});

test("a scheduled lesson can be marked as a no-show", async () => {
  const api = await signedInAs(
    teacherMe,
    detailRoutes({ "POST /lessons/4/cancel/": { status: 200, body: lesson({ id: 4, status: "no_show" }) } }),
  );
  await renderApp("/roster/7");

  await fireEvent.press(await screen.findByRole("button", { name: "Mark no-show" }));

  await waitFor(() => expect(api.callsTo("POST /lessons/4/cancel/")).toHaveLength(1));
  expect(api.callsTo("POST /lessons/4/cancel/")[0].body).toEqual({ status: "no_show" });
});

test("editing can archive the student", async () => {
  const api = await signedInAs(
    teacherMe,
    detailRoutes({ "PATCH /students/7/": { status: 200, body: student(7, { is_active: false }) } }),
  );
  await renderApp("/roster/7");

  await fireEvent.press(await screen.findByRole("button", { name: "Edit" }));
  expect((await screen.findByLabelText("First name")).props.value).toBe("Giulia");
  await fireEvent.press(screen.getByRole("radio", { name: "Archived" }));
  await fireEvent.press(screen.getByRole("button", { name: "Save" }));

  await waitFor(() => expect(api.callsTo("PATCH /students/7/")).toHaveLength(1));
  expect(api.callsTo("PATCH /students/7/")[0].body).toMatchObject({ is_active: false });
});
