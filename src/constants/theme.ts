/**
 * MusicStudio palette — converted from the OKLCH tokens in design/tokens.md
 * (React Native's StyleSheet doesn't support oklch(), so these are the
 * computed sRGB hex equivalents; keep in sync if the web palette changes).
 */
import { Platform } from "react-native";

export const Colors = {
  light: {
    text: "#231814",
    textSecondary: "#685a54",
    background: "#fcf3ee",
    backgroundElement: "#ffffff",
    backgroundMuted: "#fdf7f3",
    border: "#eadfd8",
    accent: "#ef852e",
    successText: "#154f27",
    successBg: "#ccf4d3",
    dangerText: "#9b1e22",
    dangerBg: "#ffd7d0",
    warningText: "#7b4800",
    warningBg: "#ffe8be",
  },
  dark: {
    text: "#f4ede8",
    textSecondary: "#b7aba6",
    background: "#231814",
    backgroundElement: "#2c2520",
    backgroundMuted: "#26201c",
    border: "#413933",
    accent: "#ef852e",
    successText: "#ccf4d3",
    successBg: "#1d3d26",
    dangerText: "#ffd7d0",
    dangerBg: "#4a2321",
    warningText: "#ffe8be",
    warningBg: "#4a3618",
  },
} as const;

export type ThemeColor = keyof typeof Colors.light & keyof typeof Colors.dark;

export const Fonts = {
  heading: Platform.select({ web: "Poppins_600SemiBold, sans-serif", default: "Poppins_600SemiBold" }),
  headingBold: Platform.select({ web: "Poppins_700Bold, sans-serif", default: "Poppins_700Bold" }),
  body: Platform.select({ web: "NunitoSans_400Regular, sans-serif", default: "NunitoSans_400Regular" }),
  bodyBold: Platform.select({ web: "NunitoSans_700Bold, sans-serif", default: "NunitoSans_700Bold" }),
  bodyExtraBold: Platform.select({
    web: "NunitoSans_800ExtraBold, sans-serif",
    default: "NunitoSans_800ExtraBold",
  }),
};

export const Spacing = {
  half: 2,
  one: 4,
  two: 8,
  three: 16,
  four: 24,
  five: 32,
  six: 64,
} as const;

export const Radius = {
  sm: 10,
  md: 12,
  lg: 16,
} as const;
