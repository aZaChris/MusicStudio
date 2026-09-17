import { relations, sql } from "drizzle-orm";
import {
  boolean,
  check,
  date,
  integer,
  numeric,
  pgEnum,
  pgTable,
  serial,
  text,
  timestamp,
  unique,
} from "drizzle-orm/pg-core";

export const roleEnum = pgEnum("role", ["teacher", "studio_owner", "parent"]);
export const languageEnum = pgEnum("language", ["en", "it"]);
export const lessonStatusEnum = pgEnum("lesson_status", [
  "scheduled",
  "completed",
  "cancelled",
  "no_show",
]);
export const paymentMethodEnum = pgEnum("payment_method", [
  "cash",
  "bank_transfer",
  "manual_entry",
]);
export const paymentStatusEnum = pgEnum("payment_status", ["paid", "pending", "overdue"]);

export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  email: text("email").notNull().unique(),
  passwordHash: text("password_hash").notNull(),
  role: roleEnum("role").notNull(),
  preferredLanguage: languageEnum("preferred_language").notNull().default("en"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const studios = pgTable("studios", {
  id: serial("id").primaryKey(),
  name: text("name").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const teachers = pgTable("teachers", {
  id: serial("id").primaryKey(),
  userId: integer("user_id")
    .notNull()
    .unique()
    .references(() => users.id, { onDelete: "cascade" }),
  studioId: integer("studio_id").references(() => studios.id, { onDelete: "set null" }),
  isOwner: boolean("is_owner").notNull().default(false),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const students = pgTable("students", {
  id: serial("id").primaryKey(),
  firstName: text("first_name").notNull(),
  lastName: text("last_name").notNull(),
  instrument: text("instrument").notNull(),
  teacherId: integer("teacher_id")
    .notNull()
    .references(() => teachers.id, { onDelete: "cascade" }),
  isActive: boolean("is_active").notNull().default(true),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const parentAccounts = pgTable("parent_accounts", {
  id: serial("id").primaryKey(),
  userId: integer("user_id")
    .notNull()
    .unique()
    .references(() => users.id, { onDelete: "cascade" }),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const parentStudentLinks = pgTable(
  "parent_student_links",
  {
    id: serial("id").primaryKey(),
    parentAccountId: integer("parent_account_id")
      .notNull()
      .references(() => parentAccounts.id, { onDelete: "cascade" }),
    studentId: integer("student_id")
      .notNull()
      .references(() => students.id, { onDelete: "cascade" }),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [unique().on(t.parentAccountId, t.studentId)],
);

export const packages = pgTable(
  "packages",
  {
    id: serial("id").primaryKey(),
    studentId: integer("student_id")
      .notNull()
      .references(() => students.id, { onDelete: "cascade" }),
    totalLessons: integer("total_lessons").notNull(),
    lessonsRemaining: integer("lessons_remaining").notNull(),
    purchaseDate: date("purchase_date").notNull(),
    expiryDate: date("expiry_date"),
    price: numeric("price", { precision: 8, scale: 2 }).notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [
    check(
      "package_remaining_within_total",
      sql`${t.lessonsRemaining} >= 0 AND ${t.lessonsRemaining} <= ${t.totalLessons}`,
    ),
  ],
);

export const lessons = pgTable("lessons", {
  id: serial("id").primaryKey(),
  studentId: integer("student_id")
    .notNull()
    .references(() => students.id, { onDelete: "cascade" }),
  teacherId: integer("teacher_id")
    .notNull()
    .references(() => teachers.id, { onDelete: "cascade" }),
  packageId: integer("package_id").references(() => packages.id, { onDelete: "set null" }),
  startTime: timestamp("start_time", { withTimezone: true }).notNull(),
  durationMinutes: integer("duration_minutes").notNull().default(30),
  status: lessonStatusEnum("status").notNull().default("scheduled"),
  notes: text("notes").notNull().default(""),
  reminderSentAt: timestamp("reminder_sent_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const payments = pgTable("payments", {
  id: serial("id").primaryKey(),
  studentId: integer("student_id")
    .notNull()
    .references(() => students.id, { onDelete: "cascade" }),
  packageId: integer("package_id").references(() => packages.id, { onDelete: "set null" }),
  amount: numeric("amount", { precision: 8, scale: 2 }).notNull(),
  date: date("date").notNull(),
  method: paymentMethodEnum("method").notNull(),
  status: paymentStatusEnum("status").notNull().default("pending"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

// Relations (for query-builder joins/nested selects)
export const usersRelations = relations(users, ({ one }) => ({
  teacher: one(teachers, { fields: [users.id], references: [teachers.userId] }),
  parentAccount: one(parentAccounts, { fields: [users.id], references: [parentAccounts.userId] }),
}));

export const studiosRelations = relations(studios, ({ many }) => ({
  teachers: many(teachers),
}));

export const teachersRelations = relations(teachers, ({ one, many }) => ({
  user: one(users, { fields: [teachers.userId], references: [users.id] }),
  studio: one(studios, { fields: [teachers.studioId], references: [studios.id] }),
  students: many(students),
}));

export const studentsRelations = relations(students, ({ one, many }) => ({
  teacher: one(teachers, { fields: [students.teacherId], references: [teachers.id] }),
  packages: many(packages),
  lessons: many(lessons),
  payments: many(payments),
  parentLinks: many(parentStudentLinks),
}));

export const parentAccountsRelations = relations(parentAccounts, ({ one, many }) => ({
  user: one(users, { fields: [parentAccounts.userId], references: [users.id] }),
  links: many(parentStudentLinks),
}));

export const parentStudentLinksRelations = relations(parentStudentLinks, ({ one }) => ({
  parentAccount: one(parentAccounts, {
    fields: [parentStudentLinks.parentAccountId],
    references: [parentAccounts.id],
  }),
  student: one(students, { fields: [parentStudentLinks.studentId], references: [students.id] }),
}));

export const packagesRelations = relations(packages, ({ one, many }) => ({
  student: one(students, { fields: [packages.studentId], references: [students.id] }),
  lessons: many(lessons),
  payments: many(payments),
}));

export const lessonsRelations = relations(lessons, ({ one }) => ({
  student: one(students, { fields: [lessons.studentId], references: [students.id] }),
  teacher: one(teachers, { fields: [lessons.teacherId], references: [teachers.id] }),
  package: one(packages, { fields: [lessons.packageId], references: [packages.id] }),
}));

export const paymentsRelations = relations(payments, ({ one }) => ({
  student: one(students, { fields: [payments.studentId], references: [students.id] }),
  package: one(packages, { fields: [payments.packageId], references: [packages.id] }),
}));
