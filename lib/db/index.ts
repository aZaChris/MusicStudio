import { Pool } from "pg";
import { drizzle } from "drizzle-orm/node-postgres";

import * as schema from "./schema";

// Lazy init: DATABASE_URL isn't set at build time — see the vercel-storage
// skill note on build-time safety. Never wrap this in a Proxy (breaks
// Auth.js adapter introspection); a plain lazy singleton is the safe pattern.
//
// Plain node-postgres (works against both local Postgres for tests and
// Neon's pooled connection string in prod) rather than the Neon-serverless
// HTTP driver — this app runs on the Node.js runtime (Fluid Compute), not
// Edge, so there's no need for the fetch-based transport, and this way the
// exact same driver is exercised in tests and in production.
function createDb() {
  const pool = new Pool({ connectionString: process.env.DATABASE_URL! });
  return drizzle(pool, { schema });
}

let _db: ReturnType<typeof createDb> | null = null;

export function getDb() {
  if (!_db) _db = createDb();
  return _db;
}
