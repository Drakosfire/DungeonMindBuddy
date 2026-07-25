import react from "@vitejs/plugin-react";
import { existsSync, readFileSync, statSync } from "node:fs";
import { extname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { Plugin } from "vite";
import { defineConfig } from "vitest/config";

const apiTarget = process.env.VITE_LIVE_API_PROXY_TARGET ?? "http://127.0.0.1:8000";
const appRoot = fileURLToPath(new URL(".", import.meta.url));
const repoRoot = resolve(appRoot, "../..");
const monorepoRoot = resolve(repoRoot, "..");
const landingPageBuildRoot = resolve(monorepoRoot, "LandingPage/build");
const mirewardPrepRoot = resolve(repoRoot, "evals/c2_live_prep/mireward-prep");

const BUDDY_BASE = "/dungeonbuddy";

const mimeByExtension: Record<string, string> = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".jsonl": "application/x-ndjson; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".svg": "image/svg+xml",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".map": "application/json; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
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
  "/markdown-theme-fixtures": "markdown-theme-fixtures.html",
  "/markdown-theme-fixtures.html": "markdown-theme-fixtures.html",
};

function safeResolve(base: string, requestPath: string): string | null {
  const decoded = decodeURIComponent(requestPath.replace(/^\/+/, ""));
  const target = resolve(base, decoded);
  const rel = relative(base, target);
  if (rel.startsWith("..") || rel === "..") {
    return null;
  }
  return target;
}

function serveFile(
  res: {
    statusCode: number;
    setHeader: (key: string, value: string) => void;
    end: (body: Buffer | string) => void;
  },
  filePath: string,
): boolean {
  if (!existsSync(filePath) || !statSync(filePath).isFile()) {
    return false;
  }
  res.setHeader("Content-Type", mimeByExtension[extname(filePath)] ?? "application/octet-stream");
  res.setHeader("Cache-Control", "no-store, max-age=0");
  res.end(readFileSync(filePath));
  return true;
}

function pathnameOf(url: string | undefined): string {
  return (url ?? "").split("?", 1)[0] || "/";
}

function isBuddyMount(pathname: string): boolean {
  return pathname === BUDDY_BASE || pathname.startsWith(`${BUDDY_BASE}/`);
}

function shouldBypassLanding(pathname: string): boolean {
  if (isBuddyMount(pathname)) return true;
  if (pathname.startsWith("/api")) return true;
  if (pathname.startsWith("/@") || pathname.startsWith("/node_modules") || pathname.startsWith("/src/")) {
    return true;
  }
  if (
    pathname.startsWith("/evals/")
    || pathname.startsWith("/corpus/")
    || pathname.startsWith("/Docs/")
    || pathname.startsWith("/scripts/")
    || pathname.startsWith("/saves/")
    || pathname.startsWith("/assets/")
  ) {
    return true;
  }
  if (pathname in prepPageAliases) return true;
  return false;
}

function landingPageStaticPlugin(): Plugin {
  return {
    name: "landing-page-static",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const pathname = pathnameOf(req.url);
        if (shouldBypassLanding(pathname)) {
          next();
          return;
        }
        if (!existsSync(landingPageBuildRoot)) {
          res.statusCode = 503;
          res.setHeader("Content-Type", "text/plain; charset=utf-8");
          res.end(
            "LandingPage build missing. From monorepo LandingPage/: pnpm build\n"
              + `Expected: ${landingPageBuildRoot}`,
          );
          return;
        }

        const relativePath = pathname === "/" ? "index.html" : pathname.replace(/^\/+/, "");
        const filePath = safeResolve(landingPageBuildRoot, relativePath);
        if (filePath && serveFile(res, filePath)) {
          return;
        }

        // CRA SPA fallback for LandingPage client routes (/ruleslawyer, /blog, …).
        const indexPath = resolve(landingPageBuildRoot, "index.html");
        if (serveFile(res, indexPath)) {
          return;
        }
        next();
      });
    },
  };
}

function mirewardPrepStaticPlugin(): Plugin {
  return {
    name: "mireward-prep-static",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const pathname = pathnameOf(req.url);
        const prepAlias = prepPageAliases[pathname];
        if (prepAlias) {
          if (!serveFile(res, resolve(mirewardPrepRoot, prepAlias))) {
            res.statusCode = 404;
            res.end("Not found");
          }
          return;
        }
        if (pathname.startsWith("/saves/")) {
          const savePath = safeResolve(mirewardPrepRoot, pathname.slice(1));
          if (savePath && serveFile(res, savePath)) {
            return;
          }
        }
        if (pathname.startsWith("/assets/")) {
          const assetPath = safeResolve(
            resolve(mirewardPrepRoot, "assets"),
            pathname.slice("/assets/".length),
          );
          if (assetPath && serveFile(res, assetPath)) {
            return;
          }
        }
        if (
          pathname.startsWith("/corpus/")
          || pathname.startsWith("/Docs/")
          || pathname.startsWith("/evals/")
          || pathname.startsWith("/scripts/")
        ) {
          const repoFile = safeResolve(repoRoot, pathname);
          if (repoFile && serveFile(res, repoFile)) {
            return;
          }
        }
        next();
      });
    },
  };
}

export default defineConfig({
  base: `${BUDDY_BASE}/`,
  plugins: [mirewardPrepStaticPlugin(), landingPageStaticPlugin(), react()],
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
