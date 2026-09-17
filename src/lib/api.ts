import { storage } from "./storage";

// The deployed web app's API — Constitution Principle II: the mobile app
// consumes the same /api/v1/* surface the web app's Server Components use,
// via the Bearer-token auth path added alongside the web session cookie.
const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL ?? "https://musicstudio-web.vercel.app/api/v1";

const TOKEN_KEY = "musicstudio-token";

export const tokenStorage = {
  get: () => storage.get(TOKEN_KEY),
  set: (token: string) => storage.set(TOKEN_KEY, token),
  clear: () => storage.remove(TOKEN_KEY),
};

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown) {
    super(`API error ${status}`);
    this.status = status;
    this.body = body;
  }
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await tokenStorage.get();
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(res.status, body);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
