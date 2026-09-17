import { and, eq, gte, isNull, lt } from "drizzle-orm";

import { getDb } from "../db";
import { lessons, parentAccounts, parentStudentLinks, students, users } from "../db/schema";
import { renderReminderEmail } from "./email";

// ponytail: Vercel Hobby plan only allows daily cron jobs (see vercel.json —
// a 15-min cadence was the original design but got rejected at deploy time),
// so the sweep runs once/day and catches everything in the next 48h instead
// of a narrow 24h-exact window. Upgrade to Pro + narrow this back to a
// 23h45m-24h window if per-lesson "exactly 24h before" timing matters later.
const WINDOW_START_MS = 0;
const WINDOW_END_MS = 48 * 60 * 60 * 1000;

/**
 * Daily reminder sweep (Vercel Cron, see vercel.json).
 * Idempotent via `reminderSentAt` — safe to re-run the same window twice.
 * Only `scheduled` lessons are considered (cancelled/no_show are skipped).
 */
export async function sendLessonReminders(): Promise<{ sent: number }> {
  const db = getDb();
  const now = new Date();
  const windowStart = new Date(now.getTime() + WINDOW_START_MS);
  const windowEnd = new Date(now.getTime() + WINDOW_END_MS);

  const due = await db
    .select({
      id: lessons.id,
      startTime: lessons.startTime,
      studentId: lessons.studentId,
      firstName: students.firstName,
      lastName: students.lastName,
    })
    .from(lessons)
    .innerJoin(students, eq(lessons.studentId, students.id))
    .where(
      and(
        eq(lessons.status, "scheduled"),
        gte(lessons.startTime, windowStart),
        lt(lessons.startTime, windowEnd),
        isNull(lessons.reminderSentAt),
      ),
    );

  let sent = 0;
  for (const lesson of due) {
    const recipients = await db
      .select({ email: users.email, preferredLanguage: users.preferredLanguage })
      .from(parentStudentLinks)
      .innerJoin(parentAccounts, eq(parentStudentLinks.parentAccountId, parentAccounts.id))
      .innerJoin(users, eq(parentAccounts.userId, users.id))
      .where(eq(parentStudentLinks.studentId, lesson.studentId));

    for (const recipient of recipients) {
      const { subject, body } = renderReminderEmail({
        language: recipient.preferredLanguage,
        studentName: `${lesson.firstName} ${lesson.lastName}`,
        startTime: lesson.startTime,
      });
      await sendEmail(recipient.email, subject, body);
    }

    await db.update(lessons).set({ reminderSentAt: now }).where(eq(lessons.id, lesson.id));
    sent += 1;
  }

  return { sent };
}

async function sendEmail(to: string, subject: string, body: string) {
  // ponytail: no transactional-email provider wired yet (MVP just needs a
  // demonstrable, logged send) — swap for Resend/Postmark via the Vercel
  // Marketplace when real delivery is needed.
  console.log(`[reminder email] to=${to} subject="${subject}"\n${body}`);
}
