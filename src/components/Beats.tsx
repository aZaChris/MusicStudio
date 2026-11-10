import { useEffect, useRef } from "react";
import { StyleSheet, View } from "react-native";
import Animated, { useAnimatedStyle, useSharedValue, withSequence, withTiming } from "react-native-reanimated";

import { Duration } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { useT } from "@/lib/i18n";
import { bounce } from "./Motion";
import { useReducedMotion } from "@/hooks/use-reduced-motion";

function Beat({ filled, size, onPlum }: { filled: boolean; size: number; onPlum?: boolean }) {
  const c = useTheme();
  const scale = useSharedValue(1);
  const reduced = useReducedMotion();
  const was = useRef(filled);

  // The only bounce in the system: a beat that has just been used pops 0.6 → 1.2 → 1.
  useEffect(() => {
    if (filled && !was.current && !reduced) {
      const part = Duration.slow / 2;
      scale.value = withSequence(withTiming(0.6, { duration: 0 }), withTiming(1.2, { duration: part, easing: bounce }), withTiming(1, { duration: part }));
    }
    was.current = filled;
  }, [filled, reduced, scale]);

  const animated = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));
  const fill = onPlum ? c.onPlum : c.beatOn;
  return (
    <Animated.View
      style={[
        { width: size, height: size, borderRadius: size / 2 },
        filled ? { backgroundColor: fill } : { borderWidth: size < 14 ? 1.5 : 2, borderColor: onPlum ? c.orange : c.beatEdge, backgroundColor: onPlum ? "transparent" : c.orangeSoft },
        animated,
      ]}
    />
  );
}

/** One dot per lesson of a package: filled = already used. The signature of MusicStudio. */
export function Beats({ total, used, size = "m", onPlum }: { total: number; used: number; size?: "s" | "m" | "l"; onPlum?: boolean }) {
  const t = useT();
  const dot = size === "s" ? 10 : size === "l" ? 24 : 18;
  return (
    <View
      accessible
      accessibilityRole="image"
      accessibilityLabel={t("package.beats", { used: String(used), total: String(total) })}
      style={[styles.row, { gap: size === "s" ? 4 : 6 }]}
    >
      {Array.from({ length: total }, (_, i) => (
        <Beat key={i} filled={i < used} size={dot} onPlum={onPlum} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({ row: { flexDirection: "row", flexWrap: "wrap" } });
