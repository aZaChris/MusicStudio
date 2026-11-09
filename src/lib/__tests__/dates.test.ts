import { formatDay, localDateISO } from "../dates";

// Tests run with TZ=Europe/Rome (package.json), like the app's users.
test("just after midnight in Rome the local date is today, while UTC is still yesterday", () => {
  const halfPastMidnight = new Date(2026, 10, 10, 0, 30); // 10 Nov 00:30 local
  expect(halfPastMidnight.toISOString().slice(0, 10)).toBe("2026-11-09"); // the old bug
  expect(localDateISO(halfPastMidnight)).toBe("2026-11-10");
});

test("a calendar date is shown as that same day, not shifted by the time zone", () => {
  expect(formatDay("2026-11-09", "en")).toContain("9");
  expect(formatDay("2026-11-09", "en")).toContain("2026");
});

test("months and days are zero padded", () => {
  expect(localDateISO(new Date(2026, 0, 5, 12))).toBe("2026-01-05");
});
