import { useCallback, useEffect, useMemo, type ReactNode } from "react";
import { Modal, PanResponder, Pressable, StyleSheet, View, useWindowDimensions } from "react-native";
import Animated, { runOnJS, useAnimatedStyle, useSharedValue, withTiming } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Duration, Radii } from "@/constants/theme";
import { useScheme, useTheme } from "@/hooks/use-theme";
import { outSoft } from "./Motion";
import { useReducedMotion } from "@/hooks/use-reduced-motion";

/**
 * Panel that rises from the bottom while the scrim fades in (slow in, base out). It closes on
 * the scrim, on Android back, and by dragging it down. Reduced motion: fades only.
 */
export function BottomSheet({ children, onClose, title }: { children: ReactNode; onClose: () => void; title: string }) {
  const c = useTheme();
  useScheme();
  const insets = useSafeAreaInsets();
  const { height } = useWindowDimensions();
  const reduced = useReducedMotion();
  const progress = useSharedValue(0); // 0 closed … 1 open
  const drag = useSharedValue(0);
  const closing = useSharedValue(false);

  useEffect(() => {
    progress.set(withTiming(1, { duration: reduced ? Duration.fast : Duration.slow, easing: outSoft }));
  }, [progress, reduced]);

  const close = useCallback(() => {
    if (closing.get()) return;
    closing.set(true);
    progress.set(
      withTiming(0, { duration: reduced ? Duration.fast : Duration.base, easing: outSoft }, (done) => {
        if (done) runOnJS(onClose)();
      }),
    );
  }, [closing, onClose, progress, reduced]);

  const pan = useMemo(
    () =>
      PanResponder.create({
        onMoveShouldSetPanResponder: (_, g) => g.dy > 6,
        onPanResponderMove: (_, g) => {
          drag.set(Math.max(0, g.dy));
        },
        onPanResponderRelease: (_, g) => {
          if (g.dy > 80 || g.vy > 0.8) close();
          else drag.set(withTiming(0, { duration: Duration.fast }));
        },
      }),
    [close, drag],
  );

  const scrim = useAnimatedStyle(() => ({ opacity: progress.value }));
  const sheet = useAnimatedStyle(() => ({
    opacity: reduced ? progress.value : 1,
    transform: [{ translateY: reduced ? 0 : (1 - progress.value) * height * 0.5 + drag.value }],
  }));

  return (
    <Modal transparent animationType="none" visible onRequestClose={close} statusBarTranslucent>
      <View style={styles.fill}>
        <Animated.View style={[StyleSheet.absoluteFill, { backgroundColor: c.scrim }, scrim]}>
          <Pressable style={styles.fill} onPress={close} accessible={false} />
        </Animated.View>
        <Animated.View
          accessibilityViewIsModal
          accessibilityLabel={title}
          style={[styles.sheet, { backgroundColor: c.paper, paddingBottom: 28 + insets.bottom }, sheet]}
        >
          <View {...pan.panHandlers} style={styles.gripArea} accessible={false} importantForAccessibility="no-hide-descendants">
            <View style={[styles.grip, { backgroundColor: c.line }]} />
          </View>
          {children}
        </Animated.View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1, justifyContent: "flex-end" },
  sheet: { borderTopLeftRadius: Radii.sheet, borderTopRightRadius: Radii.sheet, paddingHorizontal: 20, paddingTop: 4, gap: 16 },
  gripArea: { alignItems: "center", paddingTop: 8, paddingBottom: 4 },
  grip: { width: 44, height: 5, borderRadius: Radii.pill },
});
