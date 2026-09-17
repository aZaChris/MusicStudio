import { hash } from "bcryptjs";
import { eq } from "drizzle-orm";

import { getDb } from "../lib/db";
import {
  lessons,
  packages,
  parentAccounts,
  parentStudentLinks,
  payments,
  students,
  studios,
  teachers,
  users,
} from "../lib/db/schema";

async function getOrCreateUser(email: string, role: "teacher" | "studio_owner" | "parent") {
  const db = getDb();
  const [existing] = await db.select().from(users).where(eq(users.email, email)).limit(1);
  if (existing) return existing;
  const [created] = await db
    .insert(users)
    .values({ email, passwordHash: await hash("password123", 10), role })
    .returning();
  return created;
}

async function main() {
  const db = getDb();
  console.log("Seeding demo data…");

  const soloUser = await getOrCreateUser("solo.teacher@example.com", "teacher");
  let [soloTeacher] = await db.select().from(teachers).where(eq(teachers.userId, soloUser.id)).limit(1);
  if (!soloTeacher) {
    [soloTeacher] = await db.insert(teachers).values({ userId: soloUser.id, studioId: null }).returning();
  }

  let [studio] = await db.select().from(studios).where(eq(studios.name, "Studio di Musica Bianchi")).limit(1);
  if (!studio) {
    [studio] = await db.insert(studios).values({ name: "Studio di Musica Bianchi" }).returning();
  }

  const ownerUser = await getOrCreateUser("owner@example.com", "studio_owner");
  let [ownerTeacher] = await db.select().from(teachers).where(eq(teachers.userId, ownerUser.id)).limit(1);
  if (!ownerTeacher) {
    [ownerTeacher] = await db
      .insert(teachers)
      .values({ userId: ownerUser.id, studioId: studio.id, isOwner: true })
      .returning();
  }

  const memberUser = await getOrCreateUser("teacher2@example.com", "teacher");
  let [memberTeacher] = await db.select().from(teachers).where(eq(teachers.userId, memberUser.id)).limit(1);
  if (!memberTeacher) {
    [memberTeacher] = await db
      .insert(teachers)
      .values({ userId: memberUser.id, studioId: studio.id })
      .returning();
  }

  async function getOrCreateStudent(
    firstName: string,
    lastName: string,
    instrument: string,
    teacherId: number,
  ) {
    const [existing] = await db
      .select()
      .from(students)
      .where(eq(students.firstName, firstName))
      .limit(1);
    if (existing) return existing;
    const [created] = await db
      .insert(students)
      .values({ firstName, lastName, instrument, teacherId })
      .returning();
    return created;
  }

  const lowStudent = await getOrCreateStudent("Giulia", "Rossi", "Piano", ownerTeacher.id);
  const [lowPkg] = await db
    .select()
    .from(packages)
    .where(eq(packages.studentId, lowStudent.id))
    .limit(1);
  const lowPackage =
    lowPkg ??
    (
      await db
        .insert(packages)
        .values({
          studentId: lowStudent.id,
          totalLessons: 8,
          lessonsRemaining: 1,
          purchaseDate: new Date().toISOString().slice(0, 10),
          price: "150.00",
        })
        .returning()
    )[0];

  const normalStudent = await getOrCreateStudent("Marco", "Verdi", "Chitarra", memberTeacher.id);
  const [normalPkg] = await db
    .select()
    .from(packages)
    .where(eq(packages.studentId, normalStudent.id))
    .limit(1);
  if (!normalPkg) {
    await db.insert(packages).values({
      studentId: normalStudent.id,
      totalLessons: 8,
      lessonsRemaining: 6,
      purchaseDate: new Date().toISOString().slice(0, 10),
      price: "150.00",
    });
  }

  const soloStudent = await getOrCreateStudent("Sara", "Neri", "Violino", soloTeacher.id);
  const [soloPkg] = await db
    .select()
    .from(packages)
    .where(eq(packages.studentId, soloStudent.id))
    .limit(1);
  const soloPackage =
    soloPkg ??
    (
      await db
        .insert(packages)
        .values({
          studentId: soloStudent.id,
          totalLessons: 10,
          lessonsRemaining: 9,
          purchaseDate: new Date().toISOString().slice(0, 10),
          price: "180.00",
        })
        .returning()
    )[0];

  const todayLesson = new Date();
  todayLesson.setHours(15, 0, 0, 0);
  const [existingTodayLesson] = await db
    .select()
    .from(lessons)
    .where(eq(lessons.studentId, soloStudent.id))
    .limit(1);
  if (!existingTodayLesson) {
    await db.insert(lessons).values({
      studentId: soloStudent.id,
      teacherId: soloTeacher.id,
      packageId: soloPackage.id,
      startTime: todayLesson,
      durationMinutes: 45,
    });
  }

  const reminderLessonTime = new Date(Date.now() + 24 * 60 * 60 * 1000);
  const [existingReminderLesson] = await db
    .select()
    .from(lessons)
    .where(eq(lessons.studentId, lowStudent.id))
    .limit(1);
  if (!existingReminderLesson) {
    await db.insert(lessons).values({
      studentId: lowStudent.id,
      teacherId: ownerTeacher.id,
      startTime: reminderLessonTime,
      durationMinutes: 30,
    });
  }

  const [existingPayment] = await db
    .select()
    .from(payments)
    .where(eq(payments.studentId, normalStudent.id))
    .limit(1);
  if (!existingPayment) {
    await db.insert(payments).values({
      studentId: normalStudent.id,
      amount: "120.00",
      date: new Date().toISOString().slice(0, 10),
      method: "bank_transfer",
      status: "pending",
    });
  }

  const parentUser = await getOrCreateUser("parent@example.com", "parent");
  let [parentAccount] = await db
    .select()
    .from(parentAccounts)
    .where(eq(parentAccounts.userId, parentUser.id))
    .limit(1);
  if (!parentAccount) {
    [parentAccount] = await db.insert(parentAccounts).values({ userId: parentUser.id }).returning();
  }
  const [existingLink] = await db
    .select()
    .from(parentStudentLinks)
    .where(eq(parentStudentLinks.studentId, lowStudent.id))
    .limit(1);
  if (!existingLink) {
    await db.insert(parentStudentLinks).values({ parentAccountId: parentAccount.id, studentId: lowStudent.id });
  }

  console.log("Done. Demo logins (password: password123):");
  for (const email of [
    "solo.teacher@example.com",
    "owner@example.com",
    "teacher2@example.com",
    "parent@example.com",
  ]) {
    console.log(`  - ${email}`);
  }
  process.exit(0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
