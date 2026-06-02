import {
  BarChart,
  Callout,
  CollapsibleSection,
  Code,
  Divider,
  Grid,
  H1,
  H2,
  Pill,
  Stack,
  Stat,
  Table,
  Text,
  UsageBar,
  useCanvasState,
} from "cursor/canvas";

const CANVAS_ID = "ingested-corpus-library.canvas.tsx";

type SessionRow = {
  campaign: string;
  session: number;
  tier: string;
  canon: boolean;
  norm: boolean;
  crumb: boolean;
  memory: boolean;
  staging: boolean;
  blessed: boolean;
  genericTitle: boolean;
};

type HubRow = {
  campaign: string;
  kind: string;
  entities: number;
  readme: number;
  dossier: number;
  timeline: number;
  statblock: number;
  other: number;
};

type GapRow = { id: string; label: string; detail: string };

type LibraryPayload = {
  generatedAt: string;
  corpusRoot: string;
  totalMdFiles: number;
  retrieval: {
    manifestEntries: number;
    sourceSessions: readonly number[];
    onDiskRoutes: number;
    inManifest: number;
    notInManifest: number;
    dogfoodManifestEntries: number;
    dogfoodSourceSessions: readonly number[];
    inDogfoodManifest: number;
    notInDogfoodManifest: number;
  };
  tierCounts: Record<string, number>;
  sessions: readonly SessionRow[];
  hubs: readonly HubRow[];
  prepCounts: Record<string, number>;
  looseMdCounts: Record<string, number>;
  elderwyldMd: number;
  liveWorkspaces: readonly { session: number | null; dir: string; artifacts: readonly string[] }[];
  notInManifestSamples: readonly string[];
  gaps: readonly GapRow[];
};

const EMPTY_PAYLOAD: LibraryPayload = {
  generatedAt: "",
  corpusRoot: "",
  totalMdFiles: 0,
  retrieval: {
    manifestEntries: 0,
    sourceSessions: [],
    onDiskRoutes: 0,
    inManifest: 0,
    notInManifest: 0,
    dogfoodManifestEntries: 0,
    dogfoodSourceSessions: [],
    inDogfoodManifest: 0,
    notInDogfoodManifest: 0,
  },
  tierCounts: {},
  sessions: [],
  hubs: [],
  prepCounts: {},
  looseMdCounts: {},
  elderwyldMd: 0,
  liveWorkspaces: [],
  notInManifestSamples: [],
  gaps: [],
};

function yn(v: boolean): string {
  return v ? "yes" : "—";
}

function tierPill(tier: string): "success" | "info" | "warning" | "neutral" {
  if (tier === "full_with_staging") return "success";
  if (tier === "breadcrumb_memory") return "info";
  if (tier === "normalized_only") return "warning";
  return "neutral";
}

function tierLabel(tier: string): string {
  if (tier === "full_with_staging") return "full + staging";
  if (tier === "breadcrumb_memory") return "breadcrumb + memory";
  if (tier === "normalized_only") return "normalized only";
  return tier;
}

function sessionRowTone(row: SessionRow): "success" | "info" | "warning" | undefined {
  if (row.tier === "full_with_staging") return "success";
  if (row.tier === "breadcrumb_memory") return "info";
  if (row.campaign === "C2" && row.session >= 21) return "success";
  return undefined;
}

function SessionMatrix({ sessions }: { sessions: readonly SessionRow[] }) {
  const rows = sessions.map((s) => [
    `${s.campaign} S${s.session}`,
    <Pill key={`${s.campaign}-${s.session}-tier`} tone={tierPill(s.tier)} size="small">
      {tierLabel(s.tier)}
    </Pill>,
    yn(s.canon),
    yn(s.norm),
    yn(s.crumb),
    yn(s.memory),
    yn(s.staging),
    s.blessed ? "yes" : "—",
    s.genericTitle ? "generic" : "—",
  ]);
  const tones = sessions.map((s) => sessionRowTone(s));
  return (
    <Table
      headers={["Session", "Pipeline tier", "Canon", "Norm", "Crumb", "Memory", "Staging", "Blessed", "Title"]}
      rows={rows}
      rowTone={tones}
      columnAlign={["left", "left", "center", "center", "center", "center", "center", "center", "center"]}
      striped
      stickyHeader
    />
  );
}

export default function IngestedCorpusLibrary() {
  const [payload] = useCanvasState<LibraryPayload>("ingestedCorpusPayload", EMPTY_PAYLOAD);
  const loaded = payload.sessions.length > 0;
  const r = payload.retrieval;
  const manifestPct = r.onDiskRoutes > 0 ? Math.round((r.inManifest / r.onDiskRoutes) * 100) : 0;
  const dogfoodPct = r.onDiskRoutes > 0 ? Math.round((r.inDogfoodManifest / r.onDiskRoutes) * 100) : 0;

  if (!loaded) {
    return (
      <Stack gap={12} style={{ padding: 16 }}>
        <H1>Ingested corpus library</H1>
        <Callout tone="warning" title="No library payload loaded">
          Run{" "}
          <Code>uv run python scripts/build_ingested_corpus_library.py && uv run python -m evals.c2_live_prep.ingested_corpus_library_canvas_emit</Code>{" "}
          then reopen this canvas.
        </Callout>
      </Stack>
    );
  }

  return (
    <Stack gap={16} style={{ padding: 16 }}>
      <Stack gap={6}>
        <H1>Ingested corpus library</H1>
        <Text tone="secondary">
          Repo scan of committed ingest pipeline artifacts vs C2S23 planning retrieval manifest. Generated{" "}
          <Code>{payload.generatedAt}</Code> from <Code>{payload.corpusRoot}</Code>.
        </Text>
        <Text size="small" tone="tertiary">
          Regenerate: <Code>uv run python scripts/build_ingested_corpus_library.py</Code> then{" "}
          <Code>uv run python -m evals.c2_live_prep.ingested_corpus_library_canvas_emit</Code>
        </Text>
      </Stack>

      <Grid columns={5} gap={12}>
        <Stat label="Corpus markdown files" value={String(payload.totalMdFiles)} tone="info" />
        <Stat label="Sessions indexed" value={String(payload.sessions.length)} />
        <Stat label="Ingest routes on disk" value={String(r.onDiskRoutes)} />
        <Stat
          label="C2S23 slim overlap"
          value={`${manifestPct}%`}
          detail={`${r.inManifest} / ${r.onDiskRoutes} routes`}
          tone="warning"
        />
        <Stat
          label="Dogfood-full overlap"
          value={`${dogfoodPct}%`}
          detail={`${r.inDogfoodManifest} / ${r.onDiskRoutes} routes · ${r.dogfoodManifestEntries} entries`}
          tone="success"
        />
      </Grid>

      <Stack gap={8}>
        <H2>C2S23 retrieval manifest coverage</H2>
        <Text size="small" tone="secondary">
          Source: c2s23_planning_corpus_manifest.json · planning session 23 · source sessions{" "}
          {r.sourceSessions.join(", ")}
        </Text>
        <UsageBar
          total={r.onDiskRoutes}
          topLeftLabel={`${manifestPct}% in manifest`}
          topRightLabel={`${r.inManifest} activated · ${r.notInManifest} not activated`}
          segments={[
            { id: "in", value: r.inManifest, color: "green" },
            { id: "out", value: r.notInManifest, color: "gray" },
          ]}
        />
        <Callout tone="info" title="Manifest is a planning slice, not full corpus inventory">
          {r.manifestEntries} manifest entries activate S21–S22 play sources, hub READMEs, prep scaffold, and S23 live
          workspace. {r.notInManifest} ingest-related routes exist on disk but are outside this activation window.
        </Callout>
      </Stack>

      <Stack gap={8}>
        <H2>Dogfood-full manifest coverage</H2>
        <Text size="small" tone="secondary">
          Source: c2s23_dogfood_full_manifest.json · planning session 23 · source sessions{" "}
          {r.dogfoodSourceSessions.join(", ")}
        </Text>
        <UsageBar
          total={r.onDiskRoutes}
          topLeftLabel={`${dogfoodPct}% in dogfood-full`}
          topRightLabel={`${r.inDogfoodManifest} activated · ${r.notInDogfoodManifest} not activated`}
          segments={[
            { id: "in", value: r.inDogfoodManifest, color: "green" },
            { id: "out", value: r.notInDogfoodManifest, color: "gray" },
          ]}
        />
        <Callout tone="success" title="Hub satellites + Elderwyld activated">
          {r.dogfoodManifestEntries} manifest entries include C2 hub satellites (dossiers, timelines, statblocks) and
          the full Elderwyld world layer alongside the slim S21–S22 planning slice.
        </Callout>
      </Stack>

      <Stack gap={8}>
        <H2>Session pipeline depth by tier</H2>
        <Text size="small" tone="secondary">
          Session count at each ingest pipeline tier · both campaigns · snapshot {payload.generatedAt}
        </Text>
        <BarChart
          categories={["normalized only", "breadcrumb + memory", "full + staging"]}
          series={[
            {
              name: "Sessions",
              data: [
                payload.tierCounts.normalized_only ?? 0,
                payload.tierCounts.breadcrumb_memory ?? 0,
                payload.tierCounts.full_with_staging ?? 0,
              ],
              tone: "info",
            },
          ]}
          height={180}
        />
      </Stack>

      <Divider />

      <Stack gap={8}>
        <H2>Session pipeline matrix</H2>
        <Text size="small" tone="secondary">
          All {payload.sessions.length} sessions · Canon = top-level recap · Norm = _normalized/ · Crumb =
          _breadcrumbed/ · Memory = _session_memory/ jsonl
        </Text>
        <SessionMatrix sessions={payload.sessions} />
      </Stack>

      <Grid columns={2} gap={12}>
        <Stack gap={8}>
          <H2>Hub packages</H2>
          <Table
            headers={["Campaign", "Kind", "Entities", "README", "Dossier", "Timeline", "Statblock"]}
            rows={payload.hubs.map((h) => [
              h.campaign,
              h.kind,
              String(h.entities),
              String(h.readme),
              String(h.dossier),
              String(h.timeline),
              String(h.statblock),
            ])}
            columnAlign={["left", "left", "right", "right", "right", "right", "right"]}
            striped
          />
          <Text size="small" tone="tertiary">
            C2 prep docs: {payload.prepCounts.C2 ?? 0} · C2 loose markdown (Factions, Cards):{" "}
            {payload.looseMdCounts.C2 ?? 0}
          </Text>
        </Stack>

        <Stack gap={8}>
          <H2>Not yet in retrieval / not fully ingested</H2>
          {payload.gaps.map((g) => (
            <CollapsibleSection key={g.id} title={g.label} trailing={<Pill tone="warning" size="small">gap</Pill>}>
              <Text size="small" tone="secondary">
                {g.detail}
              </Text>
            </CollapsibleSection>
          ))}
          <Text size="small" tone="tertiary">
            Elderwyld world layer: {payload.elderwyldMd} markdown files (not in C2S23 manifest).
          </Text>
        </Stack>
      </Grid>

      <Stack gap={8}>
        <H2>Live workspaces</H2>
        <Table
          headers={["Session", "Workspace dir", "Artifacts"]}
          rows={payload.liveWorkspaces.map((w) => [
            w.session != null ? String(w.session) : "—",
            w.dir,
            w.artifacts.join(", "),
          ])}
        />
      </Stack>

      <CollapsibleSection title="Sample routes not in C2S23 manifest" count={payload.notInManifestSamples.length}>
        <Stack gap={6}>
          {payload.notInManifestSamples.map((route) => (
            <Text key={route} size="small" style={{ fontFamily: "monospace" }}>
              {route}
            </Text>
          ))}
        </Stack>
      </CollapsibleSection>

      <Text size="small" tone="quaternary">
        Canvas shell: <Code>{CANVAS_ID}</Code> · Sidecar:{" "}
        <Code>{CANVAS_ID.replace(".canvas.tsx", ".canvas.data.json")}</Code>
      </Text>
    </Stack>
  );
}
