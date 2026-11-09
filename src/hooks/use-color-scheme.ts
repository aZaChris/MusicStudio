import { useColorScheme as useRNColorScheme } from "react-native";

// A real function instead of `export { useColorScheme } from "react-native"`: the re-export
// resolved to undefined under Jest's react-native preset.
export function useColorScheme() {
  return useRNColorScheme();
}
