import '@testing-library/jest-dom/vitest'
import { cleanup, configure } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

import i18n from '../i18n'
import { session } from '../api/client'

// The whole app renders in each test; the first test of a file pays jsdom/i18n warm-up and
// can outrun the default 1 s of findBy*/waitFor on a slow machine.
configure({ asyncUtilTimeout: 10000 })

// Tests assert English text; the language detector would otherwise follow jsdom's navigator.
void i18n.changeLanguage('en')

afterEach(() => {
  cleanup()
  session.clear()
  localStorage.clear()
  vi.unstubAllGlobals()
  vi.useRealTimers()
})
