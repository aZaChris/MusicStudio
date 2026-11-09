import { fireEvent, screen, waitFor } from "@testing-library/react-native";

import { page } from "@/test/fake-api";
import { payment, student } from "@/test/fixtures";
import { renderApp, signedInAs, teacherMe } from "@/test/render";

// Only Date is faked: 10 Nov 2026, 00:30 in Rome (still 9 Nov in UTC).
const realTimers = ["setTimeout", "setInterval", "setImmediate", "clearTimeout", "clearInterval",
  "clearImmediate", "nextTick", "queueMicrotask", "requestAnimationFrame", "cancelAnimationFrame",
  "requestIdleCallback", "cancelIdleCallback", "hrtime", "performance"] as const;

beforeEach(() => jest.useFakeTimers({ now: new Date(2026, 10, 10, 0, 30), doNotFake: [...realTimers] }));
afterEach(() => jest.useRealTimers());

const routes = (post: Parameters<typeof signedInAs>[1] = {}) => ({
  "GET /payments/": { status: 200, body: page([payment(1)]) },
  "GET /students/": { status: 200, body: page([student(7, { full_name: "Giulia Rossi" })]) },
  ...post,
});

async function fillForm(amount: string) {
  await fireEvent.press(await screen.findByRole("radio", { name: "Giulia Rossi" }));
  await fireEvent.changeText(screen.getByLabelText("Amount"), amount);
  await fireEvent.press(screen.getByRole("radio", { name: "Bank transfer" }));
  await fireEvent.press(screen.getByRole("button", { name: "Register payment" }));
}

test("lists payments with translated method and status", async () => {
  await signedInAs(teacherMe, routes());
  await renderApp("/payments");

  expect(await screen.findByText("€ 120.00")).toBeOnTheScreen();
  expect(screen.getByText("Paid")).toBeOnTheScreen();
  expect(screen.getByText(/2 Nov 2026 · Bank transfer/)).toBeOnTheScreen();
});

test("a payment registered at 00:30 local time carries today's local date", async () => {
  const api = await signedInAs(
    teacherMe,
    routes({ "POST /payments/": { status: 201, body: payment(2, { date: "2026-11-10" }) } }),
  );
  await renderApp("/payments");

  await fillForm("80,50");

  await waitFor(() => expect(api.callsTo("POST /payments/")).toHaveLength(1));
  expect(api.callsTo("POST /payments/")[0].body).toEqual({
    student: 7,
    amount: "80.50",
    date: "2026-11-10",
    method: "bank_transfer",
    status: "paid",
  });
  expect(await screen.findByText("Payment registered.")).toBeOnTheScreen();
  expect(screen.getByLabelText("Amount").props.value).toBe("");
});

test("a rejected payment shows the server's reason and keeps what was typed", async () => {
  await signedInAs(
    teacherMe,
    routes({ "POST /payments/": { status: 400, body: { amount: ["Ensure that there are no more than 6 digits."] } } }),
  );
  await renderApp("/payments");

  await fillForm("99999999");

  expect(await screen.findByText(/amount: Ensure that there are no more than 6 digits\./)).toBeOnTheScreen();
  expect(screen.getByLabelText("Amount").props.value).toBe("99999999");
});
