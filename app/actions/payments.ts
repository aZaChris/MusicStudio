"use server";

import { revalidatePath } from "next/cache";

import { auth } from "@/lib/auth";
import { createPayment } from "@/lib/services/payments";

export async function registerPaymentAction(formData: FormData) {
  const session = await auth();
  if (!session || (session.user.role !== "teacher" && session.user.role !== "studio_owner")) {
    throw new Error("Forbidden");
  }

  await createPayment({
    studentId: Number(formData.get("student")),
    amount: String(formData.get("amount")),
    date: String(formData.get("date")),
    method: formData.get("method") as "cash" | "bank_transfer" | "manual_entry",
    status: "paid",
  });

  revalidatePath("/payments");
  revalidatePath("/dashboard");
  revalidatePath("/students");
}
