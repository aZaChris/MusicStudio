import * as SecureStore from "expo-secure-store";

import { session } from "@/lib/api/client";

afterEach(async () => {
  await session.clear();
  (SecureStore as unknown as { __reset: () => void }).__reset();
});
