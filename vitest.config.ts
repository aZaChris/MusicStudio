import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
  test: {
    environment: "node",
    setupFiles: ["./tests/setup.ts"],
    globals: true,
    // `pg` (TLS sockets) hangs inconsistently under Vitest's default worker
    // threads pool; child-process forks avoid it. Also run test files
    // serially — they all hit the same Neon compute and interleave deletes.
    pool: "forks",
    fileParallelism: false,
  },
});
