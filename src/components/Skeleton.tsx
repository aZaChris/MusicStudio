import { useEffect } from "react";
import { StyleSheet } from "react-native";
import Animated, { cancelAnimation, useAnimatedStyle, useSharedValue, withRepeat, withTiming } from "react-native-reanimated";

import { Radii } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { useReducedMotion } from "@/hooks/use-reduced-motion";

/** List-shaped placeholder (line-2 block, rounded, slow glint) shown while data is on its way. */
export function Skeleton({ height = 72 }: { height?: number }) {
  const c = useTheme();
  const glint = useSharedValue(0.55);
  const reduced = useReducedMotion();
  useEffect(() => {
    if (reduced) return;
    glint.value = withRepeat(withTiming(1, { duration: 900 }), -1, true);
    return () => cancelAnimation(glint);
  }, [glint, reduced]);
  const animated = useAnimatedStyle(() => ({ opacity: glint.value }));
  return <Animated.View style={[styles.base, { height, backgroundColor: c.line2 }, animated]} />;
}

const styles = StyleSheet.create({ base: { borderRadius: Radii.row } });
