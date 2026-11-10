/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    globals: true,
    // Each test renders the whole app; under parallel workers 5 s per test is too tight.
    testTimeout: 30000,
    // Every test file starts jsdom + the whole app: more than 2 workers starved a 2.7 GB machine
    // ("Failed to start forks worker").
    maxWorkers: 2,
  },
})
