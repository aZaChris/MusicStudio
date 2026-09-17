import { config } from "dotenv";

config({ path: ".env.local" });
config({ path: ".env.test", override: true });

if (!process.env.DATABASE_URL) {
  throw new Error(
    "DATABASE_URL is not set. Run `npx drizzle-kit push` against a test database first " +
      "(see README.md's testing section), then set DATABASE_URL / .env.test.",
  );
}
