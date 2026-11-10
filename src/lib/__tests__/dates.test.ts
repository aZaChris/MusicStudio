import { addMonths, formatDay, localDateISO, localDateTimeToISO, nextDays } from "../dates";

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

describe("scheduling helpers", () => {
  test("localDateTimeToISO keeps the wall-clock time across summer time", () => {
    // TZ=Europe/Rome: 16:30 is UTC+1 in winter and UTC+2 after the change on 29 Mar 2026.
    expect(localDateTimeToISO("2026-03-27", "16:30")).toBe("2026-03-27T15:30:00.000Z");
    expect(localDateTimeToISO("2026-03-30", "16:30")).toBe("2026-03-30T14:30:00.000Z");
  });

  test("nextDays starts today and crosses month ends", () => {
    expect(nextDays(3, new Date(2026, 10, 29))).toEqual(["2026-11-29", "2026-11-30", "2026-12-01"]);
  });

  test("addMonths clamps to the last day of a shorter month", () => {
    expect(addMonths("2026-11-10", 6)).toBe("2027-05-10");
    expect(addMonths("2026-08-31", 6)).toBe("2027-02-28");
    expect(addMonths("2026-11-30", 3)).toBe("2027-02-28");
  });
});
