import * as Localization from "expo-localization";
import { createContext, useContext } from "react";

import type { LessonStatus, PaymentMethod, PaymentStatus } from "./api/types";

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
    "dashboard.noUpcoming": "No upcoming lessons.",
    "roster.title": "Students",
    "roster.remaining": "remaining",
    "roster.lowPackage": "Running low",
    "roster.empty": "No active students.",
    "roster.noPackage": "No active package",
    "student.lessons": "Lessons",
    "student.noLessons": "No lessons yet.",
    "lesson.markComplete": "Mark complete",
    "lesson.note": "Progress note",
    "lesson.cancel": "Cancel",
    "lesson.status.scheduled": "Scheduled",
    "lesson.status.completed": "Completed",
    "lesson.status.cancelled": "Cancelled",
    "lesson.status.no_show": "No-show",
    "package.status.active": "Active",
    "package.status.expired": "Expired",
    "package.status.completed": "Used up",
    "payments.title": "Payments",
    "payments.registerPayment": "Register payment",
    "payments.student": "Student",
    "payments.amount": "Amount",
    "payments.date": "Date",
    "payments.method": "Method",
    "payments.empty": "No payments yet.",
    "payments.saved": "Payment registered.",
    "payments.method.cash": "Cash",
    "payments.method.bank_transfer": "Bank transfer",
    "payments.method.manual_entry": "Manual entry",
    "payments.method.card": "Card (online)",
    "payments.status.paid": "Paid",
    "payments.status.pending": "Pending",
    "payments.status.overdue": "Overdue",
    "parent.portalTitle": "Your lessons",
    "parent.lessons": "Lessons and attendance",
    "parent.paymentStatus": "Payments",
    "parent.noStudents": "No students are linked to your account yet.",
    "auth.login": "Log in",
    "auth.email": "Email",
    "auth.password": "Password",
    "auth.logout": "Log out",
    "auth.invalidCredentials": "Invalid email or password.",
    "auth.sessionExpired": "Your session has ended. Please log in again.",
    "auth.unreachable": "Cannot reach the server to check your account.",
    "common.retry": "Try again",
    "common.loading": "Loading…",
    "error.network": "Cannot reach the server. Check your connection.",
    "error.sessionExpired": "Your session has ended. Please log in again.",
    "error.forbidden": "You are not allowed to do this.",
    "error.notFound": "Not found. It may have been removed or is not visible to you.",
    "error.rateLimited": "Too many attempts. Wait a minute and try again.",
    "error.server": "The server had a problem. Try again later.",
    "error.rejected": "The server rejected the request.",
    "error.rejectedWithReason": "The server rejected the request: {reason}",
    "error.unexpected": "Something went wrong.",
  },
  it: {
    "nav.home": "Home",
    "nav.students": "Studenti",
    "nav.payments": "Pagamenti",
    "dashboard.greeting": "Ciao, {name} 👋",
    "dashboard.activeStudents": "studenti attivi",
    "dashboard.pendingPayments": "pagamenti sospesi",
    "dashboard.upcoming": "Prossime lezioni",
    "dashboard.noUpcoming": "Nessuna lezione in programma.",
    "roster.title": "Studenti",
    "roster.remaining": "rimanenti",
    "roster.lowPackage": "In esaurimento",
    "roster.empty": "Nessuno studente attivo.",
    "roster.noPackage": "Nessun pacchetto attivo",
    "student.lessons": "Lezioni",
    "student.noLessons": "Ancora nessuna lezione.",
    "lesson.markComplete": "Segna come completata",
    "lesson.note": "Nota di progresso",
    "lesson.cancel": "Annulla",
    "lesson.status.scheduled": "Programmata",
    "lesson.status.completed": "Completata",
    "lesson.status.cancelled": "Annullata",
    "lesson.status.no_show": "Assente",
    "package.status.active": "Attivo",
    "package.status.expired": "Scaduto",
    "package.status.completed": "Esaurito",
    "payments.title": "Pagamenti",
    "payments.registerPayment": "Registra pagamento",
    "payments.student": "Studente",
    "payments.amount": "Importo",
    "payments.date": "Data",
    "payments.method": "Metodo",
    "payments.empty": "Ancora nessun pagamento.",
    "payments.saved": "Pagamento registrato.",
    "payments.method.cash": "Contanti",
    "payments.method.bank_transfer": "Bonifico",
    "payments.method.manual_entry": "Inserimento manuale",
    "payments.method.card": "Carta (online)",
    "payments.status.paid": "Pagato",
    "payments.status.pending": "In sospeso",
    "payments.status.overdue": "Scaduto",
    "parent.portalTitle": "Le tue lezioni",
    "parent.lessons": "Lezioni e presenze",
    "parent.paymentStatus": "Pagamenti",
    "parent.noStudents": "Nessuno studente è ancora collegato al tuo account.",
    "auth.login": "Accedi",
    "auth.email": "Email",
    "auth.password": "Password",
    "auth.logout": "Esci",
    "auth.invalidCredentials": "Email o password non validi.",
    "auth.sessionExpired": "La sessione è terminata. Accedi di nuovo.",
    "auth.unreachable": "Impossibile raggiungere il server per verificare l'account.",
    "common.retry": "Riprova",
    "common.loading": "Caricamento…",
    "error.network": "Impossibile raggiungere il server. Controlla la connessione.",
    "error.sessionExpired": "La sessione è terminata. Accedi di nuovo.",
    "error.forbidden": "Non hai i permessi per questa operazione.",
    "error.notFound": "Non trovato. Potrebbe essere stato rimosso o non essere visibile per te.",
    "error.rateLimited": "Troppi tentativi. Aspetta un minuto e riprova.",
    "error.server": "Il server ha avuto un problema. Riprova più tardi.",
    "error.rejected": "Il server ha rifiutato la richiesta.",
    "error.rejectedWithReason": "Il server ha rifiutato la richiesta: {reason}",
    "error.unexpected": "Qualcosa è andato storto.",
  },
} satisfies Record<Locale, Record<string, string>>;

export type TranslationKey = keyof (typeof dictionaries)["en"];
export type Translate = (key: TranslationKey, vars?: Record<string, string>) => string;

export function detectLocale(): Locale {
  const tag = Localization.getLocales()[0]?.languageCode;
  return tag === "it" ? "it" : "en";
}

export function t(locale: Locale, key: TranslationKey, vars?: Record<string, string>): string {
  let text: string = dictionaries[locale][key] ?? dictionaries.en[key] ?? key;
  if (vars) {
    for (const [k, v] of Object.entries(vars)) text = text.replace(`{${k}}`, v);
  }
  return text;
}

// Enum codes from the API, always translated (constitution VI). Unknown codes fall back to
// the raw value instead of crashing if the backend adds one before the app is updated.
export const lessonStatusKey = (s: LessonStatus) => `lesson.status.${s}` as const;
export const paymentStatusKey = (s: PaymentStatus) => `payments.status.${s}` as const;
export const paymentMethodKey = (m: PaymentMethod) => `payments.method.${m}` as const;

export function enumLabel(translate: Translate, key: string): string {
  return key in dictionaries.en ? translate(key as TranslationKey) : key.split(".").pop()!;
}

export const LocaleContext = createContext<Locale>("en");

export function useLocale() {
  return useContext(LocaleContext);
}

export function useT(): Translate {
  const locale = useLocale();
  return (key, vars) => t(locale, key, vars);
}
