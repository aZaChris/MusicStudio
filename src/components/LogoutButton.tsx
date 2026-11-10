import { useAuth } from "@/lib/auth-context";
import { useT } from "@/lib/i18n";
import { IconButton } from "./IconButton";

/** Sign-out, available to every role (audit issue 4). */
export function LogoutButton() {
  const { logout } = useAuth();
  const t = useT();
  return <IconButton icon="logout" label={t("auth.logout")} onPress={logout} />;
}
