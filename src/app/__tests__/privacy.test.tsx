// Privacy screen for families, and the account screen for owners and teachers (phase 7).
import { fireEvent, screen, waitFor } from "@testing-library/react-native";
import { Share } from "react-native";

import { session } from "@/lib/api/client";
import { page } from "@/test/fake-api";
import { ownerMe, parentMe, renderApp, signedInAs, studentMe } from "@/test/render";

const consent = {
  id: 5,
  notice_version: "2026-11-draft",
  given_at: "2026-11-01T10:00:00Z",
  withdrawn_at: null,
  children: [{ id: 7, name: "Giulia Rossi" }],
};

test("consents are listed and withdrawing needs the password", async () => {
  const api = await signedInAs(parentMe, {
    "GET /privacy/consents/": { status: 200, body: [consent] },
    "POST /privacy/consents/5/withdraw/": { status: 202, body: { detail: "withdrawn" } },
  });
  await renderApp("/privacy");

  expect(await screen.findByText("Giulia Rossi")).toBeOnTheScreen();
  const withdraw = screen.getByRole("button", { name: "Withdraw consent" });
  expect(withdraw).toBeDisabled();
  await fireEvent.changeText(screen.getByLabelText(/Your password/), "password123");
  await fireEvent.press(withdraw);

  await waitFor(() => expect(api.callsTo("POST /privacy/consents/5/withdraw/")).toHaveLength(1));
  expect(api.callsTo("POST /privacy/consents/5/withdraw/")[0].body).toEqual({ password: "password123" });
});

test("the export opens the system share sheet with the JSON", async () => {
  const share = jest.spyOn(Share, "share").mockResolvedValue({ action: "sharedAction" });
  const api = await signedInAs(parentMe, {
    "GET /privacy/consents/": { status: 200, body: [] },
    "GET /privacy/export/": { status: 200, body: { account: { email: parentMe.email }, children: [] } },
  });
  await renderApp("/privacy");

  await fireEvent.press(await screen.findByRole("button", { name: "Export my data" }));

  await waitFor(() => expect(share).toHaveBeenCalled());
  expect(api.callsTo("GET /privacy/export/")).toHaveLength(1);
  expect(String(share.mock.calls[0][0].message)).toContain(parentMe.email);
  share.mockRestore();
});

test("closing the account needs the password and a confirmation, then signs out", async () => {
  const api = await signedInAs(parentMe, {
    "GET /privacy/consents/": { status: 200, body: [] },
    "POST /privacy/erase/": { status: 202, body: { detail: "erased" } },
    "POST /auth/logout/": { status: 205 },
  });
  await renderApp("/privacy");

  const erase = await screen.findByRole("button", { name: "Close my account" });
  expect(erase).toBeDisabled();
  await fireEvent.changeText(screen.getByLabelText(/Your password/), "password123");
  expect(erase).toBeDisabled(); // still needs the confirmation
  await fireEvent.press(screen.getByRole("checkbox", { name: "I understand this cannot be undone" }));
  await fireEvent.press(erase);

  expect(await screen.findByLabelText("Email")).toBeOnTheScreen(); // back on the login screen
  expect(api.callsTo("POST /privacy/erase/")[0].body).toEqual({ password: "password123" });
  expect(await session.refreshToken()).toBeNull();
});

test("an open checkout blocks the erasure with the server message", async () => {
  await signedInAs(parentMe, {
    "GET /privacy/consents/": { status: 200, body: [] },
    "POST /privacy/erase/": { status: 409, body: { detail: "An online payment is still pending." } },
  });
  await renderApp("/privacy");

  await fireEvent.changeText(await screen.findByLabelText(/Your password/), "password123");
  await fireEvent.press(screen.getByRole("checkbox", { name: "I understand this cannot be undone" }));
  await fireEvent.press(screen.getByRole("button", { name: "Close my account" }));

  expect(await screen.findByText(/online payment is still pending/)).toBeOnTheScreen();
  expect(await session.refreshToken()).toBe("refresh-1");
});

test("an adult student reaches the privacy screen from the portal", async () => {
  await signedInAs(studentMe, {
    "GET /students/": { status: 200, body: page([]) },
    "GET /privacy/consents/": { status: 200, body: [] },
  });
  await renderApp("/portal");

  await fireEvent.press(await screen.findByRole("button", { name: "Privacy" }));
  expect(await screen.findByText("Your consents")).toBeOnTheScreen();
});

const mfaOff = { "GET /auth/mfa/": { status: 200, body: { enabled: false, recovery_codes_left: 0 } } };

test("changing the password signs the teacher out", async () => {
  const api = await signedInAs(ownerMe, {
    ...mfaOff,
    "POST /auth/password/change/": { status: 200, body: { detail: "password_changed" } },
    "POST /auth/logout/": { status: 205 },
  });
  await renderApp("/account");

  await fireEvent.changeText(await screen.findByLabelText("Current password"), "old-pass-1");
  await fireEvent.changeText(screen.getByLabelText("New password"), "Contrabbasso-Rosso-88");
  await fireEvent.press(screen.getByRole("button", { name: "Change password" }));

  expect(await screen.findByLabelText("Email")).toBeOnTheScreen();
  expect(api.callsTo("POST /auth/password/change/")[0].body).toEqual({
    current_password: "old-pass-1",
    new_password: "Contrabbasso-Rosso-88",
  });
});

test("setting up two-step verification shows the secret, then the recovery codes once", async () => {
  const api = await signedInAs(ownerMe, {
    ...mfaOff,
    "POST /auth/mfa/setup/": { status: 201, body: { secret: "JBSWY3DPEHPK3PXP", otpauth_uri: "otpauth://totp/MusicStudio:t?secret=JBSWY3DPEHPK3PXP" } },
    "POST /auth/mfa/confirm/": { status: 200, body: { recovery_codes: ["aaaaaa-bbbb", "cccccc-dddd"] } },
  });
  await renderApp("/account");

  await fireEvent.press(await screen.findByRole("button", { name: "Turn on" }));
  expect(await screen.findByText("JBSWY3DPEHPK3PXP")).toBeOnTheScreen();
  await fireEvent.changeText(screen.getByLabelText("Verification code (or recovery code)"), "123456");
  await fireEvent.press(screen.getByRole("button", { name: "Confirm" }));

  expect(await screen.findByText("aaaaaa-bbbb")).toBeOnTheScreen();
  expect(api.callsTo("POST /auth/mfa/confirm/")[0].body).toEqual({ code: "123456" });
  await fireEvent.press(screen.getByRole("button", { name: "I saved them" }));
  await waitFor(() => expect(screen.queryByText("aaaaaa-bbbb")).not.toBeOnTheScreen());
});
