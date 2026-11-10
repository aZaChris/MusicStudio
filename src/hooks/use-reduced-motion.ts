import { useEffect, useState } from "react";
import { AccessibilityInfo } from "react-native";

/**
 * True when the OS asks for less motion. Then movement, scaling and bounce are switched off and
 * only fades remain (design/system/motion.md). Starts false and flips on the first answer.
 */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    let alive = true;
    AccessibilityInfo.isReduceMotionEnabled()
      .then((on) => alive && on && setReduced(true))
      .catch(() => undefined);
    const sub = AccessibilityInfo.addEventListener("reduceMotionChanged", (on) => setReduced(on));
    return () => {
      alive = false;
      sub.remove();
    };
  }, []);
  return reduced;
}
