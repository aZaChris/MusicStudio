const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

const ACCESS_TOKEN_KEY = 'musicstudio-access-token'
const REFRESH_TOKEN_KEY = 'musicstudio-refresh-token'

export const tokenStorage = {
  getAccess: () => localStorage.getItem(ACCESS_TOKEN_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_TOKEN_KEY),
  set: (access: string, refresh: string) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, access)
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh)
  },
  clear: () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  },
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
  ) {
    super(`API error ${status}`)
  }
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = tokenStorage.getRefresh()
  if (!refresh) return null

  const res = await fetch(`${API_BASE_URL}/auth/token/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  })
  if (!res.ok) {
    tokenStorage.clear()
    return null
  }
  const data = await res.json()
  localStorage.setItem(ACCESS_TOKEN_KEY, data.access)
  return data.access as string
}

export async function apiFetch<T>(path: string, options: RequestInit = {}, isRetry = false): Promise<T> {
  const access = tokenStorage.getAccess()
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(access ? { Authorization: `Bearer ${access}` } : {}),
      ...options.headers,
    },
  })

  if (res.status === 401 && !isRetry) {
    const newAccess = await refreshAccessToken()
    if (newAccess) return apiFetch<T>(path, options, true)
  }

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new ApiError(res.status, body)
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}
