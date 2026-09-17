import { attachDatabasePool } from "@vercel/functions";
import { Pool } from "pg";
import { drizzle } from "drizzle-orm/node-postgres";

import * as schema from "./schema";

// Lazy init: DATABASE_URL isn't set at build time — see the vercel-storage
// skill note on build-time safety. Never wrap this in a Proxy (breaks
// Auth.js adapter introspection); a plain lazy singleton is the safe pattern.
//
// Plain node-postgres against Neon's POOLED connection string (this app runs
// on the Node.js runtime / Fluid Compute, not Edge, so there's no need for
// the fetch-based @neondatabase/serverless transport) — same driver in tests
// (against local/branch Postgres) and prod. `attachDatabasePool` lets Fluid
// Compute close the pool cleanly on function suspend instead of leaking
// connections across invocations.
function createDb() {
  const pool = new Pool({ connectionString: process.env.DATABASE_URL! });
  attachDatabasePool(pool);
  return drizzle(pool, { schema });
}

let _db: ReturnType<typeof createDb> | null = null;

export function getDb() {
  if (!_db) _db = createDb();
  return _db;
}
