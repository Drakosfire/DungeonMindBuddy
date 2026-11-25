// Collect the complete inventory, including skipped cases omitted by Vitest list.
import { createRequire } from "node:module";
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const [output, workers, ...selectors] = process.argv.slice(2);
if (!output || !/^[1-9][0-9]*$/.test(workers) || selectors.some((s) => s.startsWith("-"))) {
  throw new Error("invalid collection arguments");
}
process.env.TEST = "true";
process.env.VITEST = "true";
process.env.NODE_ENV ??= "test";
const require = createRequire(resolve("package.json"));
const { createVitest } = await import(pathToFileURL(require.resolve("vitest/node")));
const ctx = await createVitest("test", {
  run: true, watch: false, maxWorkers: Number(workers), minWorkers: Number(workers),
});
try {
  const { testModules, unhandledErrors } = await ctx.collect(selectors);
  if (unhandledErrors.length) throw new Error("unhandled collection errors");
  const cases = [];
  for (const module of testModules) {
    for (const suite of [module, ...module.children.allSuites()]) {
      if (suite.errors().length) throw new Error(`collection error in ${module.moduleId}`);
    }
    for (const test of module.children.allTests()) {
      const state = test.result().state;
      if (!["pending", "skipped"].includes(state)) throw new Error(`unexpected collection state: ${state}`);
      cases.push({ file: module.moduleId, name: test.fullName, state });
    }
  }
  if (process.exitCode || !cases.length) throw new Error("collection failed or empty");
  await writeFile(output, JSON.stringify(cases));
} finally {
  await ctx.close();
}
