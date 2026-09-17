import { getLocale } from "@/lib/get-locale";
import { LoginForm } from "./LoginForm";

export default async function LoginPage() {
  const locale = await getLocale();
  return (
    <div style={{ display: "flex", minHeight: "100vh", alignItems: "center", justifyContent: "center" }}>
      <LoginForm locale={locale} />
    </div>
  );
}
