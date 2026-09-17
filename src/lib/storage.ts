import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

/**
 * expo-secure-store's web binding isn't fully implemented in this SDK
 * version (getValueWithKeyAsync throws) — Expo's own docs already flag web
 * SecureStore support as limited. Native (iOS/Android, the actual target
 * here) uses the real Keychain/Keystore-backed SecureStore; web falls back
 * to localStorage, which is fine for local dev/preview, never for a
 * shipped web build of this app (there isn't one — Android is the target).
 */
export const storage = {
  get: async (key: string): Promise<string | null> => {
    if (Platform.OS === "web") return globalThis.localStorage?.getItem(key) ?? null;
    return SecureStore.getItemAsync(key);
  },
  set: async (key: string, value: string): Promise<void> => {
    if (Platform.OS === "web") return void globalThis.localStorage?.setItem(key, value);
    return SecureStore.setItemAsync(key, value);
  },
  remove: async (key: string): Promise<void> => {
    if (Platform.OS === "web") return void globalThis.localStorage?.removeItem(key);
    return SecureStore.deleteItemAsync(key);
  },
};
