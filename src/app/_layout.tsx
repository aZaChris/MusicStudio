import { BricolageGrotesque_700Bold, BricolageGrotesque_800ExtraBold } from "@expo-google-fonts/bricolage-grotesque";
import { Figtree_500Medium, Figtree_600SemiBold, Figtree_700Bold } from "@expo-google-fonts/figtree";
import { QueryClientProvider } from "@tanstack/react-query";
import { useFonts } from "expo-font";
import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { useEffect, useState } from "react";

import { useTheme } from "@/hooks/use-theme";
import { AuthProvider } from "@/lib/auth-context";
import { detectLocale, LocaleContext } from "@/lib/i18n";
import { createQueryClient } from "@/lib/query-client";

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  const c = useTheme();
  const locale = detectLocale();
  // One client per app mount (not module-level): logout clears it, tests get a fresh one.
  const [queryClient] = useState(createQueryClient);

  const [fontsLoaded] = useFonts({
    BricolageGrotesque_700Bold,
    BricolageGrotesque_800ExtraBold,
    Figtree_500Medium,
    Figtree_600SemiBold,
    Figtree_700Bold,
  });

  useEffect(() => {
    if (fontsLoaded) SplashScreen.hideAsync();
  }, [fontsLoaded]);

  if (!fontsLoaded) return null;

  return (
    <QueryClientProvider client={queryClient}>
      <LocaleContext.Provider value={locale}>
        <AuthProvider>
          {/* No native headers: every screen draws its own large title. New screens slide in from
              the right and go back the other way (design/system/motion.md); with reduce-motion on,
              the OS turns the slide into a fade. */}
          <Stack screenOptions={{ headerShown: false, animation: "slide_from_right", animationDuration: 220, contentStyle: { backgroundColor: c.paper } }} />
        </AuthProvider>
      </LocaleContext.Provider>
    </QueryClientProvider>
  );
}
