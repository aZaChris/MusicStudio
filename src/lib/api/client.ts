// HTTP client and session for the Django API (ADR-M003).
//
// - The access token (15 minutes) lives only in memory; the refresh token in secure storage.
// - On a 401 the client refreshes once and retries once. Concurrent 401s share ONE refresh:
//   the backend blacklists a refresh token as soon as it is rotated, so a second parallel
//   refresh with the same token would fail and sign the user out at random.
// - When the session cannot be renewed it is cleared and listeners are told (auth context).
import { storage } from "../storage";

export const API_BASE_URL = (
  process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1"
).replace(/\/+$/, "");
const API_ORIGIN = API_BASE_URL.replace(/^(https?:\/\/[^/]+).*$/, "$1");

const REFRESH_KEY = "musicstudio.refresh";

export class ApiError extends Error {
  constructor(
    /** HTTP status; 0 when the server could not be reached. */
    readonly status: number,
    readonly detail?: string,
    readonly code?: string,
    readonly fieldErrors: Record<string, string[]> = {},
  ) {
    super(detail ?? `API error ${status}`);
    this.name = "ApiError";
  }
}

function toApiError(status: number, body: unknown): ApiError {
  if (!body || typeof body !== "object") return new ApiError(status);
  const { detail, code, ...rest } = body as Record<string, unknown>;
  const fieldErrors: Record<string, string[]> = {};
  for (const [field, value] of Object.entries(rest)) {
    if (Array.isArray(value)) fieldErrors[field] = value.map(String);
    else if (typeof value === "string") fieldErrors[field] = [value];
  }
  return new ApiError(
    status,
    typeof detail === "string" ? detail : undefined,
    typeof code === "string" ? code : undefined,
    fieldErrors,
  );
}

// --- Session ---------------------------------------------------------------------------
let accessToken: string | null = null;
let refreshing: Promise<string | null> | null = null;
const expiredListeners = new Set<() => void>();

export const session = {
  async start(tokens: { access: string; refresh: string }) {
    accessToken = tokens.access;
    await storage.set(REFRESH_KEY, tokens.refresh);
  },
  async clear() {
    accessToken = null;
    await storage.remove(REFRESH_KEY);
  },
  refreshToken: () => storage.get(REFRESH_KEY),
  /** Called when the session could not be renewed (revoked or expired refresh token). */
  onExpired(listener: () => void) {
    expiredListeners.add(listener);
    return () => void expiredListeners.delete(listener);
  },
};

async function expire() {
  await session.clear();
  expiredListeners.forEach((listener) => listener());
}

/** Single flight: every caller during a refresh awaits the same promise. */
export function refreshAccess(): Promise<string | null> {
  refreshing ??= doRefresh().finally(() => {
    refreshing = null;
  });
  return refreshing;
}

async function doRefresh(): Promise<string | null> {
  const refresh = await session.refreshToken();
  if (!refresh) return null;
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/auth/token/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ refresh }),
    });
  } catch {
    throw new ApiError(0); // offline: keep the session, the user is not signed out
  }
  if (!res.ok) {
    await expire();
    return null;
  }
  const tokens = (await res.json()) as { access: string; refresh: string };
  await session.start(tokens); // rotation: the old refresh token is now blacklisted
  return accessToken;
}

// --- Requests --------------------------------------------------------------------------
interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  /** false for login: no bearer, and a 401 means "wrong credentials", not "refresh". */
  auth?: boolean;
}

function urlFor(path: string): string {
  // `next` links from DRF are absolute; keep their path but always talk to our configured host.
  return /^https?:\/\//.test(path) ? API_ORIGIN + path.replace(/^https?:\/\/[^/]+/, "") : API_BASE_URL + path;
}

async function send(path: string, options: RequestOptions, token: string | null): Promise<Response> {
  try {
    return await fetch(urlFor(path), {
      method: options.method ?? "GET",
      headers: {
        Accept: "application/json",
        ...(options.body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    throw new ApiError(0);
  }
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const auth = options.auth ?? true;
  let token = auth ? (accessToken ?? (await refreshAccess())) : null;
  let res = await send(path, options, token);

  if (res.status === 401 && auth) {
    token = await refreshAccess();
    if (token) res = await send(path, options, token);
    if (!token || res.status === 401) {
      if (token) await expire(); // a fresh token refused: the account itself is gone
      throw new ApiError(401);
    }
  }

  if (!res.ok) throw toApiError(res.status, await res.json().catch(() => null));
  if (res.status === 204 || res.status === 205) return undefined as T;
  return (await res.json()) as T;
}

/**
 * Every page of a DRF list. ponytail: loads all pages up front — fine for 1–10 teachers
 * (~300 students for an owner); switch to useInfiniteQuery + onEndReached if lists grow.
 */
export async function fetchAllPages<T>(path: string): Promise<T[]> {
  const results: T[] = [];
  let next: string | null = path;
  while (next) {
    const page: { results: T[]; next: string | null } = await apiFetch(next);
    results.push(...page.results);
    next = page.next;
  }
  return results;
}
