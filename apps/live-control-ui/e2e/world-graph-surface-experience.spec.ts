import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

type LatencyRecord = {
  stage: string;
  t: number;
  durationMs?: number;
  meta?: Record<string, unknown>;
};

type BenchPayload = {
  measuredAt: string;
  baseURL: string;
  gitHead?: string;
  navigation: {
    plan: { domContentLoadedMs: number | null; loadEventMs: number | null };
    build: { domContentLoadedMs: number | null; loadEventMs: number | null };
  };
  stages: LatencyRecord[];
  projectionMarks: string[];
  notes: string[];
  cleanupCandidates: string[];
};

async function scrapeLatency(page: Page): Promise<LatencyRecord[]> {
  return page.evaluate(() => {
    const w = window as Window & {
      __DMB_WG_SURFACE_LATENCY__?: LatencyRecord[];
      __DMB_WG_SURFACE_LATENCY_API__?: { getRecords: () => LatencyRecord[] };
    };
    if (w.__DMB_WG_SURFACE_LATENCY_API__) {
      return w.__DMB_WG_SURFACE_LATENCY_API__.getRecords();
    }
    if (w.__DMB_WG_SURFACE_LATENCY__?.length) {
      return [...w.__DMB_WG_SURFACE_LATENCY__];
    }
    // Full-document navigations remount the app; ring is mirrored to sessionStorage.
    try {
      const raw = sessionStorage.getItem("dmb:wg-surface-latency-ring");
      if (raw) {
        const parsed = JSON.parse(raw) as LatencyRecord[];
        if (Array.isArray(parsed)) return parsed;
      }
    } catch {
      // ignore
    }
    return [];
  });
}

async function clearClientCaches(page: Page): Promise<void> {
  await page.evaluate(() => {
    const w = window as Window & {
      __DMB_WG_SURFACE_LATENCY_API__?: {
        reset: () => void;
        clearProjectionCache: () => void;
      };
    };
    w.__DMB_WG_SURFACE_LATENCY_API__?.clearProjectionCache();
    w.__DMB_WG_SURFACE_LATENCY_API__?.reset();
  });
}

async function navigationTiming(page: Page): Promise<{
  domContentLoadedMs: number | null;
  loadEventMs: number | null;
}> {
  return page.evaluate(() => {
    const nav = performance.getEntriesByType("navigation")[0] as
      | PerformanceNavigationTiming
      | undefined;
    if (!nav) return { domContentLoadedMs: null, loadEventMs: null };
    return {
      domContentLoadedMs: Math.round(nav.domContentLoadedEventEnd),
      loadEventMs: Math.round(nav.loadEventEnd),
    };
  });
}

async function projectionMarkNames(page: Page): Promise<string[]> {
  return page.evaluate(() =>
    performance
      .getEntriesByType("mark")
      .map((entry) => entry.name)
      .filter((name) => name.startsWith("dmb:wg-projection:") || name.startsWith("dmb:wg-surface:"))
      .concat(
        performance
          .getEntriesByType("measure")
          .map((entry) => entry.name)
          .filter((name) => name.startsWith("dmb:wg-projection:") || name.startsWith("dmb:wg-surface:")),
      ),
  );
}

function deriveCleanupCandidates(payload: BenchPayload): string[] {
  const stages = new Set(payload.stages.map((s) => s.stage));
  const candidates: string[] = [];
  const switchStart = payload.stages.find((s) => s.stage === "surface_switch_start");
  if (switchStart?.meta?.navigation === "full_document_anchor") {
    candidates.push(
      "Plan↔Build uses full-document `<a href>` navigation (`navigation: full_document_anchor`); SPA routing would retain the client projection TTL cache across surfaces.",
    );
  }
  if (stages.has("client_cache_miss") && !stages.has("client_cache_hit")) {
    candidates.push(
      "Cold path observed client_cache_miss with no client_cache_hit in this run — warm client TTL and/or OPT03 server completed-cache should be re-measured on a second pass without clear.",
    );
  }
  if (stages.has("detail_glance_open") && stages.has("detail_full_open")) {
    candidates.push(
      "Chip glance → Expand path is instrumented; compare detail_glance_open vs detail_full_open wall deltas vs projection re-fetch marks to see if Expand re-resolves unnecessarily.",
    );
  }
  if (!stages.has("first_chip_paint")) {
    candidates.push(
      "No first_chip_paint — Plan document in this session may lack graph-native TipTap chips; seed a chip or use a session with refs before attributing chip-path latency.",
    );
  }
  if (stages.has("build_projection_ready") && stages.has("surface_switch_start")) {
    candidates.push(
      "Surface switch → build_projection_ready includes full reload + Build campaign/document admission; split admission UI cost from projection fetch in a follow-up mark if needed.",
    );
  }
  if (candidates.length === 0) {
    candidates.push("Re-run with a chip-bearing Plan doc and a warm second pass to rank cache vs navigation costs.");
  }
  return candidates;
}

function writeArtifacts(payload: BenchPayload): void {
  const repoRoot = path.resolve(__dirname, "../../..");
  const reportDir = path.join(repoRoot, "report");
  const docsReport = path.join(
    repoRoot,
    "Docs/Reports/REPORT-world-graph-surface-experience-benchmark.md",
  );
  fs.mkdirSync(reportDir, { recursive: true });
  const jsonPath = path.join(reportDir, "world-graph-surface-experience-bench.json");
  fs.writeFileSync(jsonPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");

  const byStage = new Map<string, LatencyRecord[]>();
  for (const row of payload.stages) {
    const list = byStage.get(row.stage) ?? [];
    list.push(row);
    byStage.set(row.stage, list);
  }
  const summaryRows = [...byStage.entries()]
    .map(([stage, rows]) => {
      const withDur = rows.filter((r) => r.durationMs != null).map((r) => r.durationMs as number);
      const last = rows[rows.length - 1];
      const dur =
        withDur.length > 0
          ? String(Math.round(withDur.reduce((a, b) => a + b, 0) / withDur.length))
          : "—";
      return `| ${stage} | ${rows.length} | ${dur} | ${last.t.toFixed(1)} |`;
    })
    .join("\n");

  const detailRows = payload.stages
    .map((row) => {
      const dur = row.durationMs != null ? String(row.durationMs) : "—";
      const meta = row.meta ? `\`${JSON.stringify(row.meta)}\`` : "—";
      return `| ${row.stage} | ${dur} | ${row.t.toFixed(1)} | ${meta} |`;
    })
    .join("\n");

  const md = `# World Graph surface experience benchmark (OPT-BENCH02)

**Measured at:** ${payload.measuredAt}  
**Base URL:** ${payload.baseURL}  
**Code SHA:** ${payload.gitHead ?? "unknown"}  
**Latency scope:** browser experience (navigation + \`dmb:wg-surface:*\` / \`dmb:wg-projection:*\` marks). Service-level warm-path numbers remain OPT-BENCH01.

## Navigation timing

| Surface | DOMContentLoaded (ms) | loadEventEnd (ms) |
| --- | ---: | ---: |
| Plan (cold) | ${payload.navigation.plan.domContentLoadedMs ?? "—"} | ${payload.navigation.plan.loadEventMs ?? "—"} |
| Build (after switch) | ${payload.navigation.build.domContentLoadedMs ?? "—"} | ${payload.navigation.build.loadEventMs ?? "—"} |

## Stage summary

| Stage | count | avg durationMs | last t |
| --- | ---: | ---: | ---: |
${summaryRows || "| _(none)_ | — | — | — |"}

## Stage detail (ring buffer order)

| Stage | durationMs | t (perf.now) | meta |
| --- | ---: | ---: | --- |
${detailRows || "| _(none)_ | — | — | — |"}

## Projection / surface performance marks

${payload.projectionMarks.map((name) => `- \`${name}\``).join("\n") || "_none_"}

## Notes

${payload.notes.map((n) => `- ${n}`).join("\n") || "- (none)"}

## Cleanup candidates (measurement only — do not fix in OPT-BENCH02)

${payload.cleanupCandidates.map((c, i) => `${i + 1}. ${c}`).join("\n")}

JSON artifact: \`report/world-graph-surface-experience-bench.json\`.
`;

  fs.writeFileSync(docsReport, md, "utf8");
  // eslint-disable-next-line no-console
  console.log(`Wrote ${jsonPath}`);
  // eslint-disable-next-line no-console
  console.log(`Wrote ${docsReport}`);
}

test.describe("OPT-BENCH02 World Graph surface experience", () => {
  test("Plan cold → chip → detail → Build switch → View", async ({ page }) => {
    test.setTimeout(120_000);
    const notes: string[] = [];
    const planPath = process.env.DMB_BENCH_PLAN_PATH ?? "/plan";
    const campaignId = process.env.DMB_BENCH_CAMPAIGN_ID ?? "longmont-c2";
    const searchQuery = process.env.DMB_BENCH_SEARCH_QUERY ?? "Glowkindle";
    let planNav = { domContentLoadedMs: null as number | null, loadEventMs: null as number | null };
    let buildNav = { domContentLoadedMs: null as number | null, loadEventMs: null as number | null };
    let stages: LatencyRecord[] = [];
    let marks: string[] = [];

    try {
      await page.goto(planPath, { waitUntil: "load" });
      await clearClientCaches(page);
      await page.reload({ waitUntil: "load" });
      planNav = await navigationTiming(page);

      await page
        .waitForFunction(
          () => {
            const w = window as Window & { __DMB_WG_SURFACE_LATENCY__?: { stage: string }[] };
            return (w.__DMB_WG_SURFACE_LATENCY__ ?? []).some((r) => r.stage === "projection_ready");
          },
          null,
          { timeout: 30_000 },
        )
        .catch(() => {
          notes.push("Timed out waiting for projection_ready on Plan.");
        });

      const chip = page.getByTestId("graph-node-chip").first();
      const chipVisible = await chip
        .waitFor({ state: "visible", timeout: 8_000 })
        .then(() => true)
        .catch(() => false);
      if (chipVisible) {
        await chip.click();
        const expand = page.getByTestId("projection-expand");
        if (
          await expand
            .waitFor({ state: "visible", timeout: 10_000 })
            .then(() => true)
            .catch(() => false)
        ) {
          await expand.click();
        } else {
          notes.push("Expand not visible after chip click (full detail or host blocked).");
        }
      } else {
        notes.push("No graph-node-chip on Plan; glance/expand stages omitted for this session doc.");
      }

      // Full-document nav to Build (intentional product path under measurement).
      await page.locator('nav.app-site-nav a[href="/build"]').click();
      await page.waitForURL(/\/build/, { timeout: 30_000 });
      await page.waitForLoadState("domcontentloaded");
      buildNav = await navigationTiming(page);

      // Bare /build requires campaign admission before projection / Find existing.
      const campaignPick = page.getByRole("button", { name: campaignId });
      if (
        await campaignPick
          .waitFor({ state: "visible", timeout: 8_000 })
          .then(() => true)
          .catch(() => false)
      ) {
        notes.push(`Build required campaign pick (${campaignId}) after surface switch.`);
        await campaignPick.click();
      }

      await page
        .getByTestId("build-markdown-editor")
        .waitFor({ state: "visible", timeout: 30_000 })
        .catch(() => {
          notes.push("build-markdown-editor not visible after campaign admission.");
        });

      await page
        .waitForFunction(
          () => {
            const w = window as Window & { __DMB_WG_SURFACE_LATENCY__?: { stage: string }[] };
            return (w.__DMB_WG_SURFACE_LATENCY__ ?? []).some(
              (r) => r.stage === "build_projection_ready",
            );
          },
          null,
          { timeout: 30_000 },
        )
        .catch(() => {
          notes.push("Timed out waiting for build_projection_ready.");
        });

      const findExisting = page.getByRole("button", { name: /Find existing object/i }).first();
      if (
        await findExisting
          .waitFor({ state: "attached", timeout: 12_000 })
          .then(() => true)
          .catch(() => false)
      ) {
        // Tool-host buttons can sit outside the Playwright viewport; force is intentional for bench.
        await findExisting.click({ force: true });
      } else {
        notes.push("Find existing object tool not visible.");
      }

      const searchInput = page.locator("#graph-reference-search-input");
      if (
        await searchInput
          .waitFor({ state: "visible", timeout: 10_000 })
          .then(() => true)
          .catch(() => false)
      ) {
        if (searchQuery) {
          await searchInput.fill(searchQuery);
        }
      } else {
        notes.push("graph-reference-search input not visible after Find existing.");
      }

      await page.waitForTimeout(400);
      const viewBtn = page.getByTestId("graph-reference-view").first();
      if (
        await viewBtn
          .waitFor({ state: "visible", timeout: 12_000 })
          .then(() => true)
          .catch(() => false)
      ) {
        await viewBtn.click();
      } else {
        notes.push("graph-reference-view not visible; Build detail stage may be missing.");
      }

      await page.waitForTimeout(300);
      stages = await scrapeLatency(page);
      marks = await projectionMarkNames(page);
    } finally {
      try {
        if (stages.length === 0) {
          stages = await scrapeLatency(page).catch(() => []);
        }
        if (marks.length === 0) {
          marks = await projectionMarkNames(page).catch(() => []);
        }
      } catch {
        // page may already be closed
      }
      const payload: BenchPayload = {
        measuredAt: new Date().toISOString(),
        baseURL: process.env.DMB_BENCH_BASE_URL ?? "http://127.0.0.1:5173",
        gitHead: process.env.DMB_BENCH_GIT_HEAD,
        navigation: { plan: planNav, build: buildNav },
        stages,
        projectionMarks: marks,
        notes,
        cleanupCandidates: [],
      };
      payload.cleanupCandidates = deriveCleanupCandidates(payload);
      writeArtifacts(payload);
    }

    expect(stages.length, "expected at least one surface latency stage").toBeGreaterThan(0);
  });
});
