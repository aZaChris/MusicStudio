"use server";

import { revalidatePath } from "next/cache";

import { auth } from "@/lib/auth";
import { getActor } from "@/lib/rbac";
import { markLessonCompleted } from "@/lib/services/lessons";

export async function completeLessonAction(lessonId: number, note: string) {
  const session = await auth();
  if (!session || (session.user.role !== "teacher" && session.user.role !== "studio_owner")) {
    throw new Error("Forbidden");
  }
  const actor = await getActor(Number(session.user.id), session.user.role);

  await markLessonCompleted(actor, lessonId, note);
  revalidatePath("/dashboard");
  revalidatePath("/students");
}
