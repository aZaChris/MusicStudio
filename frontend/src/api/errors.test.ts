import { expect, test } from 'vitest'

import i18n from '../i18n'
import { ApiError } from './client'
import { errorMessage, isClientError } from './errors'

const t = i18n.getFixedT('en')

test.each([
  [0, 'Cannot reach the server'],
  [401, 'session has ended'],
  [403, 'not allowed'],
  [404, 'Not found'],
  [429, 'Too many attempts'],
  [503, 'server had a problem'],
])('status %i has a clear message', (status, text) => {
  expect(errorMessage(new ApiError(status), t)).toContain(text)
})

test("conflicts and field errors show the server's reason", () => {
  expect(errorMessage(new ApiError(409, 'Already completed.'), t)).toBe(
    'The server rejected the request: Already completed.',
  )
  expect(errorMessage(new ApiError(400, undefined, undefined, { amount: ['Too big.'] }), t)).toBe(
    'The server rejected the request: amount: Too big.',
  )
})

test('Italian messages for Italian users', () => {
  expect(errorMessage(new ApiError(403), i18n.getFixedT('it'))).toContain('Non hai i permessi')
})

test('4xx are client errors (no retry); network and 5xx are not', () => {
  expect(isClientError(new ApiError(404))).toBe(true)
  expect(isClientError(new ApiError(0))).toBe(false)
  expect(isClientError(new ApiError(500))).toBe(false)
})
