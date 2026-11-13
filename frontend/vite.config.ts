/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv, type Plugin } from 'vite'

// The canonical link and the share preview need the site's absolute address, which only the
// build knows (VITE_SITE_URL). Unset, the tags are left out: a relative one would be a broken
// link, and Vite would try to read it as a file.
function siteMeta(): Plugin {
  let site = ''
  return {
    name: 'site-meta',
    configResolved(config) {
      const env = loadEnv(config.mode, config.envDir, 'VITE_')
      site = (env.VITE_SITE_URL ?? '').replace(/\/$/, '')
    },
    transformIndexHtml() {
      if (!site) return []
      const image = `${site}/showcase/musicstudio-poster.jpg`
      return [
        { tag: 'link', attrs: { rel: 'canonical', href: `${site}/` }, injectTo: 'head' },
        { tag: 'meta', attrs: { property: 'og:url', content: `${site}/` }, injectTo: 'head' },
        { tag: 'meta', attrs: { property: 'og:image', content: image }, injectTo: 'head' },
        { tag: 'meta', attrs: { property: 'og:image:width', content: '1920' }, injectTo: 'head' },
        { tag: 'meta', attrs: { property: 'og:image:height', content: '1080' }, injectTo: 'head' },
      ]
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), siteMeta()],
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
