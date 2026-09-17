import { beforeEach, describe, expect, it } from "vitest";

import { createPayment, PaymentValidationError } from "@/lib/services/payments";
import { createPackage, createStudent, createTeacher, resetDb } from "./helpers";

beforeEach(async () => {
  await resetDb();
});

describe("createPayment", () => {
  it("rejects a package that belongs to a different student", async () => {
    const teacher = await createTeacher();
    const student = await createStudent(teacher.id);
    const otherStudent = await createStudent(teacher.id);
    const mismatchedPackage = await createPackage(otherStudent.id);

    await expect(
      createPayment({
        studentId: student.id,
        packageId: mismatchedPackage.id,
        amount: "50.00",
        date: "2026-01-10",
        method: "cash",
        status: "paid",
      }),
    ).rejects.toThrow(PaymentValidationError);
  });

  it("succeeds when the package belongs to the same student", async () => {
    const teacher = await createTeacher();
    const student = await createStudent(teacher.id);
    const pkg = await createPackage(student.id);

    const payment = await createPayment({
      studentId: student.id,
      packageId: pkg.id,
      amount: "50.00",
      date: "2026-01-10",
      method: "cash",
      status: "paid",
    });

    expect(payment.status).toBe("paid");
  });

  it("defaults to pending status when none is given", async () => {
    const teacher = await createTeacher();
    const student = await createStudent(teacher.id);

    const payment = await createPayment({
      studentId: student.id,
      amount: "30.00",
      date: "2026-01-10",
      method: "manual_entry",
    });

    expect(payment.status).toBe("pending");
  });
});
