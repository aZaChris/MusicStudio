import { QueryClientProvider } from "@tanstack/react-query";
import {
  NunitoSans_400Regular,
  NunitoSans_700Bold,
  NunitoSans_800ExtraBold,
} from "@expo-google-fonts/nunito-sans";
import { Poppins_600SemiBold, Poppins_700Bold } from "@expo-google-fonts/poppins";
import { useFonts } from "expo-font";
import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { useEffect, useState } from "react";

import { useColorScheme } from "@/hooks/use-color-scheme";
import { AuthProvider } from "@/lib/auth-context";
import { detectLocale, LocaleContext } from "@/lib/i18n";
import { createQueryClient } from "@/lib/query-client";
import { Colors } from "@/constants/theme";

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  const scheme = useColorScheme();
  const theme = Colors[scheme === "dark" ? "dark" : "light"];
  const locale = detectLocale();
  // One client per app mount (not module-level): logout clears it, tests get a fresh one.
  const [queryClient] = useState(createQueryClient);

  const [fontsLoaded] = useFonts({
    Poppins_600SemiBold,
    Poppins_700Bold,
    NunitoSans_400Regular,
    NunitoSans_700Bold,
    NunitoSans_800ExtraBold,
  });

  useEffect(() => {
    if (fontsLoaded) SplashScreen.hideAsync();
  }, [fontsLoaded]);

  if (!fontsLoaded) return null;

  return (
    <QueryClientProvider client={queryClient}>
      <LocaleContext.Provider value={locale}>
        <AuthProvider>
          <Stack
            screenOptions={{
              headerStyle: { backgroundColor: theme.backgroundElement },
              headerTintColor: theme.text,
              headerTitleStyle: { fontFamily: "Poppins_600SemiBold" },
              contentStyle: { backgroundColor: theme.background },
            }}
          >
            <Stack.Screen name="index" options={{ headerShown: false }} />
            <Stack.Screen name="login" options={{ headerShown: false }} />
            <Stack.Screen name="(teacher)" options={{ headerShown: false }} />
            <Stack.Screen name="(parent)" options={{ headerShown: false }} />
          </Stack>
        </AuthProvider>
      </LocaleContext.Provider>
    </QueryClientProvider>
  );
}
