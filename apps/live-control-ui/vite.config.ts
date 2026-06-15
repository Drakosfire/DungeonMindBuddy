import react from "@vitejs/plugin-react";
import { existsSync, readFileSync, statSync } from "node:fs";
import { extname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const apiTarget = process.env.VITE_LIVE_API_PROXY_TARGET ?? "http://127.0.0.1:8000";
const appRoot = fileURLToPath(new URL(".", import.meta.url));
const repoRoot = resolve(appRoot, "../..");
const mirewardPrepRoot = resolve(repoRoot, "evals/c2_live_prep/mireward-prep");

const mimeByExtension: Record<string, string> = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".jsonl": "application/x-ndjson; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
  ".png": "image/png",
};

const prepPageAliases: Record<string, string> = {
  "/index.html": "index.html",
  "/live-play": "live-play.html",
  "/live-play/": "live-play.html",
  "/live-play.html": "live-play.html",
  "/retrieval": "retrieval.html",
  "/retrieval/": "retrieval.html",
  "/retrieval.html": "retrieval.html",
  "/combat.html": "combat.html",
  "/live-notes.html": "live-notes.html",
  "/timeline.html": "timeline.html",
  "/locations.html": "locations.html",
  "/npcs.html": "npcs.html",
  "/roll-tables.html": "roll-tables.html",
  "/statblocks.html": "statblocks.html",
};

function safeResolve(base: string, requestPath: string): string | null {
  const decoded = decodeURIComponent(requestPath.replace(/^\/+/, ""));
  const target = resolve(base, decoded);
  const rel = relative(base, target);
  if (rel.startsWith("..") || rel === ".." || resolve(base) === target) {
    return null;
  }
  return target;
}

function serveFile(res: { statusCode: number; setHeader: (key: string, value: string) => void; end: (body: Buffer | string) => void }, filePath: string): void {
  if (!existsSync(filePath) || !statSync(filePath).isFile()) {
    res.statusCode = 404;
    res.end("Not found");
    return;
  }
  res.setHeader("Content-Type", mimeByExtension[extname(filePath)] ?? "application/octet-stream");
  res.setHeader("Cache-Control", "no-store, max-age=0");
  res.end(readFileSync(filePath));
}

function mirewardPrepStaticPlugin() {
  return {
    name: "mireward-prep-static",
    configureServer(server: { middlewares: { use: (handler: (req: { url?: string }, res: { statusCode: number; setHeader: (key: string, value: string) => void; end: (body: Buffer | string) => void }, next: () => void) => void) => void } }) {
      server.middlewares.use((req, res, next) => {
        const pathname = (req.url ?? "").split("?", 1)[0];
        const prepAlias = prepPageAliases[pathname];
        if (prepAlias) {
          serveFile(res, resolve(mirewardPrepRoot, prepAlias));
          return;
        }
        if (pathname.startsWith("/saves/")) {
          const savePath = safeResolve(mirewardPrepRoot, pathname.slice(1));
          if (savePath) {
            serveFile(res, savePath);
            return;
          }
        }
        if (pathname.startsWith("/assets/")) {
          const assetPath = safeResolve(resolve(mirewardPrepRoot, "assets"), pathname.slice("/assets/".length));
          if (assetPath) {
            serveFile(res, assetPath);
            return;
          }
        }
        if (
          pathname.startsWith("/corpus/") ||
          pathname.startsWith("/Docs/") ||
          pathname.startsWith("/evals/") ||
          pathname.startsWith("/scripts/")
        ) {
          const repoFile = safeResolve(repoRoot, pathname);
          if (repoFile) {
            serveFile(res, repoFile);
            return;
          }
        }
        next();
      });
    },
  };
}

export default defineConfig({
  plugins: [mirewardPrepStaticPlugin(), react()],
  server: {
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: true,
  },
});
