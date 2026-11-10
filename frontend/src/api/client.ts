// HTTP client and session for the Django API (ADR-023).
//
// - The access token (15 minutes) lives only in memory; the refresh token in localStorage
//   (accepted risk, owner decision: see ADR-023 for the httpOnly-cookie next step).
// - The backend blacklists a refresh token as soon as it rotates, so:
//   * the rotated refresh token is stored after EVERY refresh (the old SPA forgot it and
//     logged users out after ~30 minutes);
//   * only one refresh runs at a time: concurrent 401s in a tab share one promise, and tabs
//     take a Web Lock, re-reading the stored token inside it (another tab may have rotated).
// - On a 401 the request is retried once; if the session cannot be renewed it is cleared and
//   listeners (the auth context) are told.

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1').replace(
  /\/+$/,
  '',
)
const API_ORIGIN = API_BASE_URL.replace(/^(https?:\/\/[^/]+).*$/, '$1')

const REFRESH_KEY = 'musicstudio.refresh'
// Keys of the old build: drop them so a stale access token is never sent again.
for (const legacy of ['musicstudio-access-token', 'musicstudio-refresh-token']) {
  localStorage.removeItem(legacy)
}

export class ApiError extends Error {
  readonly status: number
  readonly detail?: string
  readonly code?: string
  readonly fieldErrors: Record<string, string[]>

  constructor(status: number, detail?: string, code?: string, fieldErrors: Record<string, string[]> = {}) {
    super(detail ?? `API error ${status}`)
    this.name = 'ApiError'
    this.status = status // 0 = the server could not be reached
    this.detail = detail
    this.code = code
    this.fieldErrors = fieldErrors
  }
}

function toApiError(status: number, body: unknown): ApiError {
  if (!body || typeof body !== 'object') return new ApiError(status)
  const { detail, code, ...rest } = body as Record<string, unknown>
  const fieldErrors: Record<string, string[]> = {}
  for (const [field, value] of Object.entries(rest)) {
    if (Array.isArray(value)) fieldErrors[field] = value.map(String)
    else if (typeof value === 'string') fieldErrors[field] = [value]
  }
  return new ApiError(
    status,
    typeof detail === 'string' ? detail : undefined,
    typeof code === 'string' ? code : undefined,
    fieldErrors,
  )
}

// --- Session ---------------------------------------------------------------------------
let accessToken: string | null = null
let refreshing: Promise<string | null> | null = null
const expiredListeners = new Set<() => void>()

export const session = {
  start(tokens: { access: string; refresh: string }) {
    accessToken = tokens.access
    localStorage.setItem(REFRESH_KEY, tokens.refresh)
  },
  clear() {
    accessToken = null
    localStorage.removeItem(REFRESH_KEY)
  },
  refreshToken: () => localStorage.getItem(REFRESH_KEY),
  onExpired(listener: () => void) {
    expiredListeners.add(listener)
    return () => void expiredListeners.delete(listener)
  },
}

function expire() {
  session.clear()
  expiredListeners.forEach((listener) => listener())
}

/** One refresh at a time: shared promise in this tab, Web Lock across tabs. */
export function refreshAccess(): Promise<string | null> {
  refreshing ??= withCrossTabLock(doRefresh).finally(() => {
    refreshing = null
  })
  return refreshing
}

function withCrossTabLock<T>(fn: () => Promise<T>): Promise<T> {
  const locks = (globalThis.navigator as Navigator | undefined)?.locks
  return locks ? locks.request('musicstudio-refresh', fn) : fn()
}

async function doRefresh(): Promise<string | null> {
  const refresh = session.refreshToken() // read inside the lock: another tab may have rotated it
  if (!refresh) return null
  let res: Response
  try {
    res = await fetch(`${API_BASE_URL}/auth/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ refresh }),
    })
  } catch {
    throw new ApiError(0) // offline: keep the session
  }
  if (!res.ok) {
    expire()
    return null
  }
  const tokens = (await res.json()) as { access: string; refresh: string }
  session.start(tokens) // rotation: store the new refresh token, the old one is blacklisted
  return accessToken
}

// --- Requests --------------------------------------------------------------------------
export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  /** false for login: no bearer, and a 401 means "wrong credentials", not "refresh". */
  auth?: boolean
}

function urlFor(path: string): string {
  // DRF `next` links are absolute: keep their path, always talk to the configured host.
  return /^https?:\/\//.test(path) ? API_ORIGIN + path.replace(/^https?:\/\/[^/]+/, '') : API_BASE_URL + path
}

async function send(path: string, options: RequestOptions, token: string | null): Promise<Response> {
  try {
    return await fetch(urlFor(path), {
      method: options.method ?? 'GET',
      headers: {
        Accept: 'application/json',
        ...(options.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    })
  } catch {
    throw new ApiError(0)
  }
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const auth = options.auth ?? true
  let token = auth ? (accessToken ?? (await refreshAccess())) : null
  let res = await send(path, options, token)

  if (res.status === 401 && auth) {
    token = await refreshAccess()
    if (token) res = await send(path, options, token)
    if (!token || res.status === 401) {
      if (token) expire() // a fresh token refused: the account itself is gone
      throw new ApiError(401)
    }
  }

  if (!res.ok) throw toApiError(res.status, await res.json().catch(() => null))
  if (res.status === 204 || res.status === 205) return undefined as T
  return (await res.json()) as T
}

/**
 * Every page of a DRF list. ponytail: loads all pages up front — fine for 1–10 teachers
 * (~300 students for an owner); switch to useInfiniteQuery if lists grow.
 */
export async function fetchAllPages<T>(path: string): Promise<T[]> {
  const results: T[] = []
  let next: string | null = path
  while (next) {
    const page: { results: T[]; next: string | null } = await apiFetch(next)
    results.push(...page.results)
    next = page.next
  }
  return results
}
