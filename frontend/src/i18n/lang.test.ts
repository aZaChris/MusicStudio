import { expect, test } from 'vitest'

import i18n from './index'

test('the page language follows the app language', async () => {
  await i18n.changeLanguage('it')
  expect(document.documentElement.lang).toBe('it')
  await i18n.changeLanguage('en')
  expect(document.documentElement.lang).toBe('en')
})
