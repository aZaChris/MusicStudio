import { NextResponse } from "next/server";

import { sendLessonReminders } from "@/lib/services/reminders";

export async function GET(request: Request) {
  const authHeader = request.headers.get("authorization");
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const result = await sendLessonReminders();
  return NextResponse.json(result);
}
