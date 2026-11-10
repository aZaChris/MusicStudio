/**
 * MusicStudio design system, for React Native. Colours, spacing, radii and motion are generated
 * from design/system/tokens.json (npm run tokens); the rest of this file is what a stylesheet
 * cannot express: font files per weight and the text styles.
 */
import { Platform, type TextStyle } from "react-native";

import { Colors } from "./tokens.generated";

export { Colors, Curves, Duration, Radii, Space } from "./tokens.generated";

export type ThemeColors = Record<keyof (typeof Colors)["light"], string>;
export type ThemeColor = keyof ThemeColors;

// One font file per weight: React Native does not synthesise weights from a single family.
export const Fonts = {
  display: "BricolageGrotesque_800ExtraBold",
  displayBold: "BricolageGrotesque_700Bold",
  body: "Figtree_500Medium",
  bodySemi: "Figtree_600SemiBold",
  bodyBold: "Figtree_700Bold",
} as const;

// `lineHeight` in tokens.json is a ratio; React Native wants pixels. Letter spacing em → px.
const style = (family: string, size: number, ratio: number, em = 0): TextStyle => ({
  fontFamily: family,
  fontSize: size,
  lineHeight: Math.round(size * ratio),
  letterSpacing: em * size,
});

export const Type = {
  display: style(Fonts.display, 56, 1, -0.02),
  titleXl: style(Fonts.display, 40, 1.05, -0.02),
  title: style(Fonts.display, 34, 1.1, -0.01),
  heading: style(Fonts.displayBold, 22, 1.2),
  number: style(Fonts.display, 44, 1),
  amount: style(Fonts.display, 19, 1.2),
  bodyLg: style(Fonts.body, 18, 1.5),
  body: style(Fonts.body, 16, 1.45),
  bodyStrong: style(Fonts.bodyBold, 16, 1.4),
  small: style(Fonts.bodySemi, 13, 1.4),
  label: { ...style(Fonts.bodyBold, 12, 1.3, 0.08), textTransform: "uppercase" } as TextStyle,
} as const;

/** Soft shadows only on what floats (tokens.json `shadow`). */
export function shadow(kind: "card" | "float", scheme: "light" | "dark") {
  const light = scheme === "light";
  const colour = kind === "float" ? (light ? "#b4531a" : "#000000") : light ? "#2b1d14" : "#000000";
  const opacity = kind === "float" ? (light ? 0.3 : 0.45) : light ? 0.1 : 0.35;
  const offset = kind === "float" ? 10 : 12;
  const radius = kind === "float" ? 24 : 32;
  return Platform.select({
    web: { boxShadow: `0 ${offset}px ${radius}px ${colour}${Math.round(opacity * 255).toString(16).padStart(2, "0")}` },
    default: {
      shadowColor: colour,
      shadowOpacity: opacity,
      shadowRadius: radius / 2,
      shadowOffset: { width: 0, height: offset },
      elevation: kind === "float" ? 8 : 6,
    },
  }) as object;
}
