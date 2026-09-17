import * as Localization from "expo-localization";
import { createContext, useContext } from "react";

export type Locale = "en" | "it";

const dictionaries = {
  en: {
    "nav.home": "Home",
    "nav.students": "Students",
    "nav.payments": "Payments",
    "dashboard.greeting": "Hi, {name} 👋",
    "dashboard.activeStudents": "active students",
    "dashboard.pendingPayments": "pending payments",
    "dashboard.upcoming": "Upcoming lessons",
    "roster.title": "Students",
    "roster.remaining": "remaining",
    "roster.lowPackage": "Running low",
    "lesson.markComplete": "Mark complete",
    "lesson.note": "Progress note",
    "lesson.cancel": "Cancel",
    "lesson.statusScheduled": "Scheduled",
    "lesson.statusCompleted": "Completed",
    "lesson.statusCancelled": "Cancelled",
    "lesson.statusNoShow": "No-show",
    "payments.title": "Payments",
    "payments.registerPayment": "Register payment",
    "payments.amount": "Amount",
    "payments.date": "Date",
    "payments.method": "Method",
    "payments.statusPaid": "Paid",
    "payments.statusPending": "Pending",
    "payments.statusOverdue": "Overdue",
    "parent.portalTitle": "Your lessons",
    "parent.upcomingLessons": "Upcoming lessons",
    "parent.attendance": "Attendance history",
    "parent.paymentStatus": "Payment status",
    "parent.noStudents": "No students are linked to your account yet.",
    "auth.login": "Log in",
    "auth.email": "Email",
    "auth.password": "Password",
    "auth.logout": "Log out",
    "auth.invalidCredentials": "Invalid credentials",
  },
  it: {
    "nav.home": "Home",
    "nav.students": "Studenti",
    "nav.payments": "Pagamenti",
    "dashboard.greeting": "Ciao, {name} 👋",
    "dashboard.activeStudents": "studenti attivi",
    "dashboard.pendingPayments": "pagamenti sospesi",
    "dashboard.upcoming": "Prossime lezioni",
    "roster.title": "Studenti",
    "roster.remaining": "rimanenti",
    "roster.lowPackage": "In esaurimento",
    "lesson.markComplete": "Segna come completata",
    "lesson.note": "Nota di progresso",
    "lesson.cancel": "Annulla",
    "lesson.statusScheduled": "Programmata",
    "lesson.statusCompleted": "Completata",
    "lesson.statusCancelled": "Annullata",
    "lesson.statusNoShow": "Assente",
    "payments.title": "Pagamenti",
    "payments.registerPayment": "Registra pagamento",
    "payments.amount": "Importo",
    "payments.date": "Data",
    "payments.method": "Metodo",
    "payments.statusPaid": "Pagato",
    "payments.statusPending": "In sospeso",
    "payments.statusOverdue": "Scaduto",
    "parent.portalTitle": "Le tue lezioni",
    "parent.upcomingLessons": "Prossime lezioni",
    "parent.attendance": "Storico presenze",
    "parent.paymentStatus": "Stato pagamento",
    "parent.noStudents": "Nessuno studente è ancora collegato al tuo account.",
    "auth.login": "Accedi",
    "auth.email": "Email",
    "auth.password": "Password",
    "auth.logout": "Esci",
    "auth.invalidCredentials": "Credenziali non valide",
  },
} satisfies Record<Locale, Record<string, string>>;

export type TranslationKey = keyof (typeof dictionaries)["en"];

export function detectLocale(): Locale {
  const tag = Localization.getLocales()[0]?.languageCode;
  return tag === "it" ? "it" : "en";
}

export function t(locale: Locale, key: TranslationKey, vars?: Record<string, string>): string {
  let text = dictionaries[locale][key] ?? dictionaries.en[key] ?? key;
  if (vars) {
    for (const [k, v] of Object.entries(vars)) text = text.replace(`{${k}}`, v);
  }
  return text;
}

export const LocaleContext = createContext<Locale>("en");

export function useLocale() {
  return useContext(LocaleContext);
}

export function useT() {
  const locale = useLocale();
  return (key: TranslationKey, vars?: Record<string, string>) => t(locale, key, vars);
}
