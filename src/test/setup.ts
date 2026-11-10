import { configure } from "@testing-library/react-native";
import * as SecureStore from "expo-secure-store";

import { session } from "@/lib/api/client";

// Animations run in a native runtime that jest does not have. Worklets needs its mock before
// reanimated loads; expo-router's test library then swaps reanimated for reanimated's own mock,
// where withTiming jumps to its end value and calls its callback at once.
// eslint-disable-next-line @typescript-eslint/no-require-imports
jest.mock("react-native-worklets", () => require("react-native-worklets/src/mock"));
jest.mock("expo-haptics", () => ({
  impactAsync: jest.fn(() => Promise.resolve()),
  ImpactFeedbackStyle: { Light: "light" },
}));

// The whole app renders in each test; on a slow machine or CI runner with parallel workers the
// default 1 s for findBy*/waitFor is too short and fails tests for timing, not behaviour.
configure({ asyncUtilTimeout: 5000 });

afterEach(async () => {
  await session.clear();
  (SecureStore as unknown as { __reset: () => void }).__reset();
});
