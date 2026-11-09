import { useSyncExternalStore } from "react";
import { useColorScheme as useRNColorScheme } from "react-native";

const noSubscription = () => () => {};

/**
 * The static web build is rendered on the server without a color scheme. During hydration we
 * must render "light" like the server did, then the real scheme. useSyncExternalStore's server
 * snapshot does exactly that without a setState inside an effect (the lint error inherited
 * from the Expo template).
 */
export function useColorScheme() {
  const isClient = useSyncExternalStore(noSubscription, () => true, () => false);
  const colorScheme = useRNColorScheme();
  return isClient ? colorScheme : "light";
}
