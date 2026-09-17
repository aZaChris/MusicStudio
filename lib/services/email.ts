const TEMPLATES = {
  en: {
    subject: "Upcoming lesson reminder — MusicStudio",
    body: (studentName: string, startTime: Date) =>
      `Hi,\n\nThis is a reminder that ${studentName}'s lesson is scheduled for ${startTime.toLocaleString("en-US")}.\n\n— MusicStudio`,
  },
  it: {
    subject: "Promemoria lezione — MusicStudio",
    body: (studentName: string, startTime: Date) =>
      `Ciao,\n\nti ricordiamo che la lezione di ${studentName} è in programma per ${startTime.toLocaleString("it-IT")}.\n\n— MusicStudio`,
  },
} as const;

export function renderReminderEmail(input: {
  language: "en" | "it";
  studentName: string;
  startTime: Date;
}) {
  const t = TEMPLATES[input.language] ?? TEMPLATES.en;
  return { subject: t.subject, body: t.body(input.studentName, input.startTime) };
}
