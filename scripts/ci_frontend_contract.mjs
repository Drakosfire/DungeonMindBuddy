// The pinned Node-only CI container consumes the same command manifest as Python.
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { performance } from "node:perf_hooks";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const catalog = JSON.parse(readFileSync(resolve(root, "ci/contracts.json"), "utf8"));
if (catalog.version !== 1) throw new Error("unsupported CI contract version");
const revision = spawnSync("git", ["rev-parse", "HEAD"], { cwd: root, encoding: "utf8" });
// The slim Node container has no Git. GitHub supplies the actual checkout SHA.
const sha = revision.status === 0 ? revision.stdout.trim() : process.env.GITHUB_SHA;
if (!sha) throw new Error("checkout SHA required for frontend contract report");
for (const step of catalog.contracts["hosted-frontend"].steps) {
  console.log(JSON.stringify({ sha, contract: "hosted-frontend", ...step, event: "start" }));
  const started = performance.now();
  const result = spawnSync(step.argv[0], step.argv.slice(1), { cwd: resolve(root, step.cwd), stdio: "inherit" });
  const exitCode = result.status ?? 1;
  console.log(JSON.stringify({ sha, contract: "hosted-frontend", elapsed_seconds: (performance.now() - started) / 1000, exit_code: exitCode }));
  if (exitCode !== 0) process.exit(exitCode);
}
