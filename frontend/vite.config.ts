/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv, type Plugin } from 'vite'

// The only pages a visitor can open without signing in and that are worth finding on a search
// engine. Nothing else is listed: no login, no private pages, no API, no media files (the brand
// video is never named in the sitemap or in the page metadata).
const PUBLIC_PAGES = ['/', '/register']

// The canonical link, the share preview, robots.txt and the sitemap need the site's absolute
// address, which only the build knows (VITE_SITE_URL). Unset, the tags and the sitemap are left
// out: a relative one would be a broken link, and Vite would try to read it as a file.
function siteMeta(): Plugin {
  let site = ''
  return {
    name: 'site-meta',
    configResolved(config) {
      const env = loadEnv(config.mode, config.envDir, 'VITE_')
      site = (env.VITE_SITE_URL ?? '').replace(/\/$/, '')
    },
    generateBundle() {
      const robots = ['User-agent: *', 'Allow: /']
      if (site) {
        const urls = PUBLIC_PAGES.map((path) => `  <url><loc>${site}${path}</loc></url>`).join('\n')
        const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`
        this.emitFile({ type: 'asset', fileName: 'sitemap.xml', source: xml })
        robots.push('', `Sitemap: ${site}/sitemap.xml`)
      }
      // Allow everything: whether the site may be indexed is decided by the X-Robots-Tag header
      // (ROBOTS_TAG, noindex by default). A Disallow would stop crawlers from seeing the noindex.
      this.emitFile({ type: 'asset', fileName: 'robots.txt', source: `${robots.join('\n')}\n` })
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
