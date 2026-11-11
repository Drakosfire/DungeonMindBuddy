import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const appRoot = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  root: appRoot,
  base: "/",
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 4183,
    strictPort: true,
  },
  preview: {
    host: "127.0.0.1",
    port: 4183,
    strictPort: true,
  },
  build: {
    outDir: process.env.NATIVE_DEMO_BUILD_OUTDIR ?? resolve(appRoot, "dist-native-demo"),
    emptyOutDir: true,
    rollupOptions: {
      input: resolve(appRoot, "native-demo.html"),
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: true,
    include: ["src/nativeGraphDemo/**/*.test.ts", "src/nativeGraphDemo/**/*.test.tsx"],
  },
});
