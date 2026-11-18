import { defineConfig } from "@playwright/test";

const portOverride = process.env.BUDDY_UI_VISUAL_PORT;
const port = Number(portOverride ?? 5184);
if (!/^[0-9]+$/.test(portOverride ?? "5184") || !Number.isInteger(port) || port < 1024 || port > 65535) {
  throw new Error("BUDDY_UI_VISUAL_PORT must be an integer from 1024 to 65535.");
}
const baseURL = `http://127.0.0.1:${port}`;
const previewDir = `../../out/ui-visual-ladle-${port}`;

export default defineConfig({
  testDir: "./tests",
  testMatch: "ui-visual.pw.ts",
  workers: 1,
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  outputDir: portOverride ? `../../out/ui-visual-playwright-${port}` : "../../out/ui-visual-playwright",
  snapshotPathTemplate: "{testDir}/ui-visual-snapshots/{arg}{ext}",
  updateSnapshots: "none",
  expect: { toHaveScreenshot: { animations: "disabled", caret: "hide" } },
  use: { baseURL },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
  webServer: {
    command: `npm run ui:build -- --outDir ${previewDir} && npx ladle preview --outDir ${previewDir} --host 127.0.0.1 --port ${port}`,
    url: `${baseURL}/meta.json`,
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
