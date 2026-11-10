import { Colors, type ThemeColors } from "@/constants/theme";
import { useColorScheme } from "@/hooks/use-color-scheme";

export function useScheme(): "light" | "dark" {
  const scheme = useColorScheme();
  return scheme === "dark" ? "dark" : "light";
}

/** The colour tokens of the active theme (light or dark). */
export function useTheme(): ThemeColors {
  return Colors[useScheme()];
}
