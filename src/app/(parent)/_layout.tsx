import { Redirect, Stack } from "expo-router";

import { useAuth } from "@/lib/auth-context";

export default function ParentLayout() {
  const { user, status } = useAuth();

  if (status === "loading") return null;
  if (!user) return <Redirect href="/login" />;
  if (user.role !== "parent" && user.role !== "student") return <Redirect href="/(teacher)/home" />;

  return <Stack screenOptions={{ headerShown: false }} />;
}
