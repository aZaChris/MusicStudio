import * as Haptics from "expo-haptics";

/** A light tap after an action that saves (motion.md). Never throws: no haptics, no problem. */
export function savedTap() {
  try {
    void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => undefined);
  } catch {
    // web and simulators without a haptic engine
  }
}
