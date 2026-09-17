import { registerPaymentAction } from "@/app/actions/payments";
import { Sidebar } from "@/components/Sidebar";
import { auth } from "@/lib/auth";
import { t, type TranslationKey } from "@/lib/i18n";
import { getLocale } from "@/lib/get-locale";
import { getActor } from "@/lib/rbac";
import { listPaymentsForActor } from "@/lib/services/payments";
import { listStudentsForActor } from "@/lib/services/students";

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export default async function PaymentsPage() {
  const session = await auth();
  const locale = await getLocale();
  if (!session) return null;

  const actor = await getActor(Number(session.user.id), session.user.role);
  const [payments, students] = await Promise.all([listPaymentsForActor(actor), listStudentsForActor(actor)]);
  const today = new Date().toISOString().slice(0, 10);

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <div style={{ flex: 1, padding: "36px 44px", maxWidth: 1280, display: "flex", flexDirection: "column", gap: 24 }}>
        <h1 style={{ fontFamily: "var(--ms-font-heading)", fontSize: 22, fontWeight: 600 }}>{t(locale, "payments.title")}</h1>

        <form
          action={registerPaymentAction}
          style={{
            display: "flex",
            gap: 8,
            alignItems: "flex-end",
            flexWrap: "wrap",
            border: "1px solid var(--ms-border)",
            borderRadius: "var(--ms-radius-lg)",
            padding: 16,
          }}
        >
          <label>
            {t(locale, "roster.student")}
            <select name="student" required defaultValue="">
              <option value="" disabled />
              {students.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.fullName}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t(locale, "payments.amount")}
            <input type="number" name="amount" step="0.01" required />
          </label>
          <label>
            {t(locale, "payments.date")}
            <input type="date" name="date" defaultValue={today} required />
          </label>
          <label>
            {t(locale, "payments.method")}
            <select name="method" defaultValue="cash">
              <option value="cash">cash</option>
              <option value="bank_transfer">bank_transfer</option>
              <option value="manual_entry">manual_entry</option>
            </select>
          </label>
          <button type="submit">{t(locale, "payments.registerPayment")}</button>
        </form>

        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left", fontSize: 12.5, color: "var(--ms-text-muted)" }}>
              <th style={{ padding: "10px 8px" }}>{t(locale, "roster.student")}</th>
              <th style={{ padding: "10px 8px" }}>{t(locale, "payments.amount")}</th>
              <th style={{ padding: "10px 8px" }}>{t(locale, "payments.date")}</th>
              <th style={{ padding: "10px 8px" }}>{t(locale, "payments.status")}</th>
            </tr>
          </thead>
          <tbody>
            {payments.map((payment) => (
              <tr key={payment.id} style={{ borderTop: "1px solid var(--ms-border)", fontSize: 14 }}>
                <td style={{ padding: "10px 8px" }}>
                  {payment.studentFirstName} {payment.studentLastName}
                </td>
                <td style={{ padding: "10px 8px" }}>{payment.amount}</td>
                <td style={{ padding: "10px 8px" }}>{payment.date}</td>
                <td style={{ padding: "10px 8px" }}>
                  {t(locale, `payments.status${capitalize(payment.status)}` as TranslationKey)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
