import { ApiError } from "../api/client";
import { errorMessage, isClientError } from "../errors";
import { t } from "../i18n";

const en = (key: Parameters<typeof t>[1], vars?: Record<string, string>) => t("en", key, vars);

test.each([
  [0, "Cannot reach the server"],
  [401, "session has ended"],
  [403, "not allowed"],
  [404, "Not found"],
  [429, "Too many attempts"],
  [503, "server had a problem"],
])("status %i has a clear message", (status, text) => {
  expect(errorMessage(new ApiError(status), en)).toContain(text);
});

test("conflicts show the server's reason", () => {
  expect(errorMessage(new ApiError(409, "Already completed."), en)).toBe(
    "The server rejected the request: Already completed.",
  );
});

test("field errors show the field and its first message", () => {
  const error = new ApiError(400, undefined, undefined, { amount: ["A valid number is required."] });
  expect(errorMessage(error, en)).toContain("amount: A valid number is required.");
});

test("non-field errors show only the message", () => {
  const error = new ApiError(400, undefined, undefined, { non_field_errors: ["Package already paid."] });
  expect(errorMessage(error, en)).toBe("The server rejected the request: Package already paid.");
});

test("Italian messages for Italian users", () => {
  expect(errorMessage(new ApiError(403), (k, v) => t("it", k, v))).toContain("Non hai i permessi");
});

test("anything that is not an ApiError is 'unexpected'", () => {
  expect(errorMessage(new Error("boom"), en)).toBe("Something went wrong.");
});

test("4xx are client errors (no retry), network and 5xx are not", () => {
  expect(isClientError(new ApiError(404))).toBe(true);
  expect(isClientError(new ApiError(0))).toBe(false);
  expect(isClientError(new ApiError(500))).toBe(false);
});
