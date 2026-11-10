// Press feedback shared by every tappable thing: squeeze to 96% and back (motion.md).
import type { ReactNode } from "react";
import { Pressable, type PressableProps, type StyleProp, type ViewStyle } from "react-native";
import Animated, { Easing, useAnimatedStyle, useSharedValue, withTiming } from "react-native-reanimated";

import { Curves, Duration } from "@/constants/theme";
import { useReducedMotion } from "@/hooks/use-reduced-motion";

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

export const outSoft = Easing.bezier(...Curves.outSoft);
export const bounce = Easing.bezier(...Curves.bounce);

export function PressScale({
  children,
  style,
  to = 0.96,
  ...rest
}: Omit<PressableProps, "style" | "children"> & { children: ReactNode; style?: StyleProp<ViewStyle>; to?: number }) {
  const scale = useSharedValue(1);
  const reduced = useReducedMotion();
  const animated = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));
  return (
    <AnimatedPressable
      {...rest}
      onPressIn={(e) => {
        if (!reduced) scale.set(withTiming(to, { duration: Duration.fast, easing: outSoft }));
        rest.onPressIn?.(e);
      }}
      onPressOut={(e) => {
        scale.set(withTiming(1, { duration: Duration.fast, easing: outSoft }));
        rest.onPressOut?.(e);
      }}
      style={[style, animated]}
    >
      {children}
    </AnimatedPressable>
  );
}
