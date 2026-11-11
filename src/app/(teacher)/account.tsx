import { LogoutButton } from "@/components/LogoutButton";
import { MfaPanel } from "@/components/account/MfaPanel";
import { PasswordChangeForm } from "@/components/account/PasswordChangeForm";
import { Screen, ScreenHeader } from "@/components/Screen";
import { useT } from "@/lib/i18n";

/** Owners and teachers: password and two-step verification. */
export default function AccountScreen() {
  const t = useT();
  return (
    <Screen>
      <ScreenHeader title={t("nav.account")} right={<LogoutButton />} />
      <PasswordChangeForm />
      <MfaPanel />
    </Screen>
  );
}
