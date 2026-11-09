// A fake Django API at the fetch boundary (ADR-M005). Tests declare routes; the real client,
// session and error mapping run unchanged.
import { API_BASE_URL } from "@/lib/api/client";

export interface FakeRequest {
  method: string;
  path: string; // without the base URL, with the query string
  body: unknown;
  authorization: string | null;
}
type Reply = { status: number; body?: unknown };
type Handler = Reply | ((req: FakeRequest) => Reply | Promise<Reply>);

export interface FakeApi {
  calls: FakeRequest[];
  /** Add or replace routes, keyed "METHOD /path/?query" (exact) or "METHOD /path/" (any query). */
  route(routes: Record<string, Handler>): void;
  callsTo(key: string): FakeRequest[];
}

export function installFakeApi(routes: Record<string, Handler> = {}): FakeApi {
  const table: Record<string, Handler> = { ...routes };
  const calls: FakeRequest[] = [];

  global.fetch = jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const path = url.startsWith(API_BASE_URL) ? url.slice(API_BASE_URL.length) : url;
    const method = init?.method ?? "GET";
    const headers = (init?.headers ?? {}) as Record<string, string>;
    const req: FakeRequest = {
      method,
      path,
      body: typeof init?.body === "string" ? JSON.parse(init.body) : undefined,
      authorization: headers.Authorization ?? null,
    };
    calls.push(req);
    const handler = table[`${method} ${path}`] ?? table[`${method} ${path.split("?")[0]}`];
    if (!handler) throw new Error(`No fake route for ${method} ${path}`);
    const reply = typeof handler === "function" ? await handler(req) : handler;
    return {
      ok: reply.status >= 200 && reply.status < 300,
      status: reply.status,
      json: async () => {
        if (reply.body === undefined) throw new SyntaxError("Unexpected end of JSON input");
        return reply.body;
      },
    } as Response;
  }) as typeof fetch;

  return {
    calls,
    route: (more) => Object.assign(table, more),
    callsTo: (key) => calls.filter((c) => `${c.method} ${c.path}`.startsWith(key)),
  };
}

/** A DRF page. */
export const page = <T>(results: T[], next: string | null = null) => ({
  count: results.length,
  next,
  previous: null,
  results,
});
