import { describe, expect, test, vi } from 'vitest'

import { ApiError, apiFetch, fetchAllPages, session } from './client'
import { installFakeApi, offline, page } from '../test/fake-api'

const rotated = { access: 'access-2', refresh: 'refresh-2' }
const okWithNewToken = (req: { authorization: string | null }) =>
  req.authorization === 'Bearer access-2' ? { status: 200, body: { ok: true } } : { status: 401 }

describe('session', () => {
  test('authenticated requests carry the bearer token', async () => {
    session.start({ access: 'access-1', refresh: 'refresh-1' })
    const api = installFakeApi({ 'GET /auth/me/': { status: 200, body: { id: 1 } } })

    await apiFetch('/auth/me/')

    expect(api.calls[0].authorization).toBe('Bearer access-1')
  })

  test('a 401 refreshes once, STORES THE ROTATED refresh token and retries', async () => {
    session.start({ access: 'expired', refresh: 'refresh-1' })
    const api = installFakeApi({
      'POST /auth/token/refresh/': { status: 200, body: rotated },
      'GET /dashboard/': okWithNewToken,
    })

    await expect(apiFetch('/dashboard/')).resolves.toEqual({ ok: true })

    expect(api.callsTo('POST /auth/token/refresh/')[0].body).toEqual({ refresh: 'refresh-1' })
    // The old SPA kept refresh-1, already blacklisted by the server: logged out at the next renewal.
    expect(session.refreshToken()).toBe('refresh-2')
  })

  test('three concurrent 401s share a single refresh', async () => {
    session.start({ access: 'expired', refresh: 'refresh-1' })
    const api = installFakeApi({
      'POST /auth/token/refresh/': async () => {
        await new Promise((r) => setTimeout(r, 10))
        return { status: 200, body: rotated }
      },
      'GET /a/': okWithNewToken,
      'GET /b/': okWithNewToken,
      'GET /c/': okWithNewToken,
    })

    await Promise.all([apiFetch('/a/'), apiFetch('/b/'), apiFetch('/c/')])

    expect(api.callsTo('POST /auth/token/refresh/')).toHaveLength(1)
  })

  test('the refresh reads the stored token at call time (another tab may have rotated it)', async () => {
    session.start({ access: 'expired', refresh: 'refresh-1' })
    localStorage.setItem('musicstudio.refresh', 'rotated-by-other-tab')
    const api = installFakeApi({
      'POST /auth/token/refresh/': { status: 200, body: rotated },
      'GET /dashboard/': okWithNewToken,
    })

    await apiFetch('/dashboard/')

    expect(api.callsTo('POST /auth/token/refresh/')[0].body).toEqual({ refresh: 'rotated-by-other-tab' })
  })

  test('refreshes run under a cross-tab Web Lock when the browser has one', async () => {
    session.start({ access: 'expired', refresh: 'refresh-1' })
    const request = vi.fn((_name: string, fn: () => Promise<unknown>) => fn())
    vi.stubGlobal('navigator', { ...navigator, locks: { request } })
    installFakeApi({ 'POST /auth/token/refresh/': { status: 200, body: rotated }, 'GET /x/': okWithNewToken })

    await apiFetch('/x/')

    expect(request).toHaveBeenCalledWith('musicstudio-refresh', expect.any(Function))
  })

  test('a refused refresh clears the session and tells the listeners', async () => {
    session.start({ access: 'expired', refresh: 'refresh-1' })
    installFakeApi({
      'POST /auth/token/refresh/': { status: 401, body: { detail: 'Token is blacklisted' } },
      'GET /dashboard/': { status: 401 },
    })
    const expired = vi.fn()
    const stop = session.onExpired(expired)

    await expect(apiFetch('/dashboard/')).rejects.toMatchObject({ status: 401 })

    expect(expired).toHaveBeenCalledTimes(1)
    expect(session.refreshToken()).toBeNull()
    stop()
  })

  test('an unreachable server is status 0 and does not sign the user out', async () => {
    session.start({ access: 'access-1', refresh: 'refresh-1' })
    offline()

    await expect(apiFetch('/dashboard/')).rejects.toMatchObject({ status: 0 })
    expect(session.refreshToken()).toBe('refresh-1')
  })

  test('login does not try to refresh on 401: it means wrong credentials', async () => {
    const api = installFakeApi({
      'POST /auth/token/': { status: 401, body: { detail: 'No active account' } },
    })

    await expect(apiFetch('/auth/token/', { method: 'POST', body: {}, auth: false })).rejects.toMatchObject({
      status: 401,
    })
    expect(api.callsTo('POST /auth/token/refresh/')).toHaveLength(0)
  })

  test('the access token is never written to localStorage', async () => {
    session.start({ access: 'access-1', refresh: 'refresh-1' })
    expect(Object.values({ ...localStorage })).not.toContain('access-1')
  })
})

describe('responses', () => {
  test('errors keep detail, code and field errors', async () => {
    session.start({ access: 'a', refresh: 'r' })
    installFakeApi({
      'POST /payments/': { status: 400, body: { amount: ['A valid number is required.'] } },
      'POST /lessons/1/complete/': { status: 409, body: { detail: 'Already completed.', code: 'conflict' } },
    })

    const fieldError = (await apiFetch('/payments/', { method: 'POST', body: {} }).catch(
      (e) => e,
    )) as ApiError
    expect(fieldError.fieldErrors).toEqual({ amount: ['A valid number is required.'] })
    await expect(apiFetch('/lessons/1/complete/', { method: 'POST', body: {} })).rejects.toMatchObject({
      status: 409,
      detail: 'Already completed.',
      code: 'conflict',
    })
  })

  test('205 resolves without a body', async () => {
    session.start({ access: 'a', refresh: 'r' })
    installFakeApi({ 'POST /auth/logout/': { status: 205 } })

    await expect(
      apiFetch('/auth/logout/', { method: 'POST', body: { refresh: 'r' } }),
    ).resolves.toBeUndefined()
  })

  test('fetchAllPages follows absolute DRF next links but always talks to the configured API', async () => {
    session.start({ access: 'a', refresh: 'r' })
    const api = installFakeApi({
      'GET /students/?is_active=true': {
        status: 200,
        body: page([{ id: 1 }], 'http://internal-host/api/v1/students/?is_active=true&page=2'),
      },
      'GET /students/?is_active=true&page=2': { status: 200, body: page([{ id: 2 }]) },
    })

    await expect(fetchAllPages('/students/?is_active=true')).resolves.toEqual([{ id: 1 }, { id: 2 }])
    expect(api.calls.map((c) => c.path)).toEqual([
      '/students/?is_active=true',
      '/students/?is_active=true&page=2',
    ])
  })
})
