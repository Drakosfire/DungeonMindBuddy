import { defineConfig } from "@playwright/test";

if (!process.env.QUALIFICATION_BASE_URL || !process.env.QUALIFICATION_OUTPUT) {
  throw new Error("Qualification requires the exact running image URL and owned output path");
}
export default defineConfig({
  testDir: ".", testMatch: "*.pw.ts", workers: 1, fullyParallel: false, retries: 0,
  timeout: 60_000, outputDir: process.env.QUALIFICATION_OUTPUT,
  reporter: [["list"], ["junit", { outputFile: `${process.env.QUALIFICATION_OUTPUT}/junit.xml` }]],
  use: { baseURL: process.env.QUALIFICATION_BASE_URL, browserName: "chromium", trace: "retain-on-failure", screenshot: "only-on-failure" },
});
