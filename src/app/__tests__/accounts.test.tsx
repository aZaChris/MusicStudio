// Sign-in with a second factor, unconfirmed accounts, forgotten password and invitations (phase 7).
import { fireEvent, screen, waitFor } from "@testing-library/react-native";

import { session } from "@/lib/api/client";
import { tokenFrom } from "@/lib/invitation";
import { installFakeApi, page } from "@/test/fake-api";
import { ownerMe, renderApp, studentMe } from "@/test/render";

test("a sign-in that needs a second factor asks for the code and then signs in", async () => {
  const api = installFakeApi({
    "POST /auth/token/": { status: 200, body: { mfa_required: true, mfa_token: "signed-mfa" } },
    "POST /auth/mfa/verify/": { status: 200, body: { access: "a", refresh: "r" } },
    "GET /auth/me/": { status: 200, body: ownerMe },
    "GET /dashboard/": {
      status: 200,
      body: { week: [], upcoming: [], pending_payments_count: 0, active_students_count: 3, low_package_students: [] },
    },
  });
  await renderApp("/login");

  await fireEvent.changeText(await screen.findByLabelText("Email"), "titolare@example.com");
  await fireEvent.changeText(screen.getByLabelText("Password"), "password123");
  await fireEvent.press(screen.getByRole("button", { name: "Log in" }));
  await fireEvent.changeText(await screen.findByLabelText("Verification code (or recovery code)"), "123456");
  await fireEvent.press(screen.getByRole("button", { name: "Log in" }));

  expect(await screen.findByText("Hi, titolare")).toBeOnTheScreen();
  expect(api.callsTo("POST /auth/mfa/verify/")[0].body).toEqual({ mfa_token: "signed-mfa", code: "123456" });
  expect(await session.refreshToken()).toBe("r");
});

test("a wrong second-factor code says so and keeps the user on the code step", async () => {
  installFakeApi({
    "POST /auth/token/": { status: 200, body: { mfa_required: true, mfa_token: "signed-mfa" } },
    "POST /auth/mfa/verify/": { status: 401, body: { detail: "Invalid code.", code: "invalid_mfa" } },
  });
  await renderApp("/login");

  await fireEvent.changeText(await screen.findByLabelText("Email"), "t@example.com");
  await fireEvent.changeText(screen.getByLabelText("Password"), "password123");
  await fireEvent.press(screen.getByRole("button", { name: "Log in" }));
  await fireEvent.changeText(await screen.findByLabelText("Verification code (or recovery code)"), "000000");
  await fireEvent.press(screen.getByRole("button", { name: "Log in" }));

  expect(await screen.findByText("The code is not valid. Try again.")).toBeOnTheScreen();
  expect(await session.refreshToken()).toBeNull();
});

test("an unconfirmed account can ask for the confirmation link again", async () => {
  const api = installFakeApi({
    "POST /auth/token/": { status: 401, body: { detail: "Confirm your email address before signing in.", code: "email_not_confirmed" } },
    "POST /auth/confirm-email/resend/": { status: 202, body: { detail: "check_email" } },
  });
  await renderApp("/login");

  await fireEvent.changeText(await screen.findByLabelText("Email"), "new@example.com");
  await fireEvent.changeText(screen.getByLabelText("Password"), "password123");
  await fireEvent.press(screen.getByRole("button", { name: "Log in" }));
  await fireEvent.press(await screen.findByRole("button", { name: "Send the link again" }));

  expect(await screen.findByText("We sent you a new confirmation link.")).toBeOnTheScreen();
  expect(api.callsTo("POST /auth/confirm-email/resend/")[0].body).toEqual({ email: "new@example.com" });
});

test("forgot password gives the same answer for any address", async () => {
  const api = installFakeApi({ "POST /auth/password-reset/": { status: 202, body: { detail: "check_email" } } });
  await renderApp("/forgot-password");

  await fireEvent.changeText(await screen.findByLabelText("Email"), "anyone@example.com");
  await fireEvent.press(screen.getByRole("button", { name: "Send the link" }));

  expect(await screen.findByText(/If the address is registered/)).toBeOnTheScreen();
  expect(api.callsTo("POST /auth/password-reset/")[0].body).toEqual({ email: "anyone@example.com" });
});

const lookup = { role: "parent", studio_name: "Scuola Zanotti", email: "anna@example.com", student_first_names: ["Giulia"], existing_account: false };

test("a parent opens the invitation link, accepts with consent and ends up signed in", async () => {
  const api = installFakeApi({
    "GET /invitations/lookup/": { status: 200, body: lookup },
    "POST /invitations/accept/": { status: 201, body: { access: "a", refresh: "r" } },
    "GET /auth/me/": { status: 200, body: { ...studentMe, role: "parent", parent_account: { id: 1 } } },
    "GET /students/": { status: 200, body: page([]) },
  });
  await renderApp("/accept-invitation?token=secret-token");

  expect(await screen.findByText("Scuola Zanotti invites you as a parent.")).toBeOnTheScreen();
  const accept = screen.getByRole("button", { name: "Accept invitation" });
  expect(accept).toBeDisabled();
  await fireEvent.changeText(screen.getByLabelText("First name"), "Anna");
  await fireEvent.changeText(screen.getByLabelText("Password"), "Pianoforte-Verde-31");
  await fireEvent.press(screen.getByRole("checkbox", { name: "I accept the terms and the privacy notice" }));
  await fireEvent.press(screen.getByRole("checkbox", { name: /I consent to the processing/ }));
  await fireEvent.press(screen.getByRole("button", { name: "Accept invitation" }));

  expect(await screen.findByText("No students are linked to your account yet.")).toBeOnTheScreen();
  expect(api.callsTo("GET /invitations/lookup/")[0].path).toContain("token=secret-token");
  expect(api.callsTo("POST /invitations/accept/")[0].body).toMatchObject({ token: "secret-token", first_name: "Anna", accept_terms: true, consent: true });
});

test("an invalid invitation says so", async () => {
  installFakeApi({ "GET /invitations/lookup/": { status: 404, body: { detail: "Not found." } } });
  await renderApp("/accept-invitation?token=old");

  expect(await screen.findByText(/not valid, has expired or was already used/)).toBeOnTheScreen();
});

test("the invitation token is read from a whole pasted link or a bare token", () => {
  expect(tokenFrom("https://app.example.com/invitations/accept?token=abc_-123")).toBe("abc_-123");
  expect(tokenFrom("  abc_-123 ")).toBe("abc_-123");
  expect(tokenFrom("https://x/y?uid=1&token=a%2Bb&z=2")).toBe("a+b");
});

test("an adult student lands on the family portal", async () => {
  installFakeApi({
    "POST /auth/token/": { status: 200, body: { access: "a", refresh: "r" } },
    "GET /auth/me/": { status: 200, body: studentMe },
    "GET /students/": { status: 200, body: page([]) },
  });
  await renderApp("/login");

  await fireEvent.changeText(await screen.findByLabelText("Email"), "luca@example.com");
  await fireEvent.changeText(screen.getByLabelText("Password"), "password123");
  await fireEvent.press(screen.getByRole("button", { name: "Log in" }));

  await waitFor(() => expect(screen.getByText("No students are linked to your account yet.")).toBeOnTheScreen());
});
