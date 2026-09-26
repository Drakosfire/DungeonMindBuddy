import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  testMatch: "ui-visual.pw.ts",
  workers: 1,
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  outputDir: "../../out/ui-visual-playwright",
  snapshotPathTemplate: "{testDir}/ui-visual-snapshots/{arg}{ext}",
  updateSnapshots: "none",
  expect: { toHaveScreenshot: { animations: "disabled", caret: "hide" } },
  use: { baseURL: "http://127.0.0.1:5184" },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
  webServer: {
    command: "npm run ui:build && npx ladle preview --host 127.0.0.1 --port 5184",
    url: "http://127.0.0.1:5184/meta.json",
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
