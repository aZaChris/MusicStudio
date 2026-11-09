import { configure } from "@testing-library/react-native";
import * as SecureStore from "expo-secure-store";

import { session } from "@/lib/api/client";

// The whole app renders in each test; on a slow machine or CI runner with parallel workers the
// default 1 s for findBy*/waitFor is too short and fails tests for timing, not behaviour.
configure({ asyncUtilTimeout: 5000 });

afterEach(async () => {
  await session.clear();
  (SecureStore as unknown as { __reset: () => void }).__reset();
});
