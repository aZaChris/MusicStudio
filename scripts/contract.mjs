#!/usr/bin/env node
// Keep the app's copy of the backend OpenAPI contract and the generated types in sync (ADR-M002).
//
//   node scripts/contract.mjs sync    copy the contract from the backend branch, regenerate types
//   node scripts/contract.mjs check   fail if either file differs from what sync would produce
//
// The backend contract lives at backend/openapi.yaml on branch refactor/production-standards.
// The local branch is preferred (it may hold unpushed contract fixes); CI only has origin/<branch>.
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const BRANCH = "refactor/production-standards";
const SOURCE = "backend/openapi.yaml";
const CONTRACT = "contract/openapi.yaml";
const TYPES = "src/lib/api/schema.d.ts";
// Pinned and run through npx: its typescript@^5 peer conflicts with the project's TypeScript 6.
const GENERATOR = "openapi-typescript@7.13.0";

function backendContract() {
  for (const ref of [BRANCH, `origin/${BRANCH}`]) {
    try {
      return execFileSync("git", ["show", `${ref}:${SOURCE}`], {
        encoding: "utf8",
        stdio: ["ignore", "pipe", "ignore"],
      });
    } catch {
      // try the next ref
    }
  }
  throw new Error(`Cannot read ${SOURCE} from ${BRANCH} (fetch the branch first).`);
}

function generateTypes(contractPath) {
  const out = join(mkdtempSync(join(tmpdir(), "contract-")), "schema.d.ts");
  execFileSync("npx", ["--yes", GENERATOR, contractPath, "-o", out], { stdio: "ignore" });
  return "// Generated from contract/openapi.yaml by scripts/contract.mjs. Do not edit.\n" +
    readFileSync(out, "utf8");
}

const command = process.argv[2];
if (command === "sync") {
  writeFileSync(CONTRACT, backendContract());
  writeFileSync(TYPES, generateTypes(CONTRACT));
  console.log(`Synced ${CONTRACT} and ${TYPES} from ${BRANCH}.`);
} else if (command === "check") {
  const problems = [];
  if (readFileSync(CONTRACT, "utf8") !== backendContract()) {
    problems.push(`${CONTRACT} differs from ${BRANCH}:${SOURCE}`);
  }
  if (readFileSync(TYPES, "utf8") !== generateTypes(CONTRACT)) {
    problems.push(`${TYPES} is not what ${GENERATOR} generates from ${CONTRACT}`);
  }
  if (problems.length) {
    console.error(problems.map((p) => `✗ ${p}`).join("\n"));
    console.error("Run: npm run contract:sync");
    process.exit(1);
  }
  console.log("✓ Contract and generated types are up to date.");
} else {
  console.error("Usage: node scripts/contract.mjs sync|check");
  process.exit(2);
}
