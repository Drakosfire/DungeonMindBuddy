import {
  Callout,
  Card,
  CardBody,
  CardHeader,
  Code,
  Divider,
  Grid,
  H1,
  H3,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  useCanvasState,
  useHostTheme,
} from "cursor/canvas";

const CANVAS_ID = "live-query-telemetry-trace-session22.canvas.tsx";

type EvidenceRow = {
  evidence_id?: string;
  path?: string;
  path_basename?: string;
  session?: number | null;
  source_role?: string;
  line_start?: number | null;
  line_end?: number | null;
  final_score?: number | null;
  text_excerpt?: string;
  reason_code?: string;
};

type ManifestRow = {
  route_basename?: string;
  source_role?: string;
  session_scope?: readonly number[];
  final_score?: number | null;
  session_scope_score?: number | null;
  source_role_score?: number | null;
  exact_title_match_score?: number | null;
};

type TraceDetail = {
  artifact_path: string;
  artifact_basename: string;
  format: string;
  question: string;
  target_session?: number | null;
  status: string;
  llm_model: string;
  warnings: readonly string[];
  quality: {
    label: string;
    session22_closing_beat_signal: boolean;
    conical_hill_drift_signal: boolean;
    cited_sessions?: readonly number[];
  };
  enhancement?: {
    source?: string;
    effective_question?: string;
    response_output_text?: string;
    prompt_excerpt?: string;
  };
  retrieval: {
    retrieval_query: string;
    admitted_count: number;
    rejected_count: number;
    top_admitted: readonly EvidenceRow[];
    top_rejected: readonly EvidenceRow[];
    retrieval_trace_summary: {
      asks_for_last_or_final?: boolean;
      asks_for_play_event?: boolean;
      session_numbers?: readonly number[];
      top_manifest_entries?: readonly ManifestRow[];
    } | null;
  };
  answer: { text: string; prompt_excerpt?: string; response_output_text?: string };
  citations: readonly EvidenceRow[];
  cited_evidence_ids: readonly string[];
  transition_rows: readonly (readonly string[])[];
};

type QuerySummary = {
  question: string;
  target_session?: number | null;
  artifact_path: string;
  artifact_basename: string;
  format: string;
  status: string;
  quality_label: string;
  admitted_count: number;
  rejected_count: number;
  citation_count: number;
  answer_preview: string;
  warnings: readonly string[];
  has_enhancement: boolean;
  llm_model: string;
};

type QueryRow = {
  query_id: string;
  default_expanded: boolean;
  summary: QuerySummary;
  detail: TraceDetail;
};

type CanvasPayload = {
  queries: readonly QueryRow[];
};

const EMPTY_PAYLOAD: CanvasPayload = { queries: [] };

function pillTone(label: string): "success" | "warning" | "info" {
  if (label === "aligned") return "success";
  if (label === "drift") return "warning";
  return "info";
}

function calloutTone(label: string): "success" | "warning" | "danger" | "info" {
  if (label === "aligned") return "success";
  if (label === "drift") return "danger";
  return "info";
}

function MonoBlock({ value }: { value: string }) {
  const theme = useHostTheme();
  if (!value.trim()) return null;
  return (
    <Text
      size="small"
      style={{
        fontFamily: "monospace",
        whiteSpace: "pre-wrap",
        border: `1px solid ${theme.stroke.secondary}`,
        borderRadius: 8,
        padding: 10,
      }}
    >
      {value}
    </Text>
  );
}

function evidenceRows(rows: readonly EvidenceRow[], withScore: boolean): string[][] {
  return rows.map((row) => {
    const line =
      row.line_start != null
        ? `L${row.line_start}${row.line_end != null && row.line_end !== row.line_start ? `-${row.line_end}` : ""}`
        : "";
    const cells = [
      row.evidence_id || "",
      row.path_basename || "",
      row.session != null ? String(row.session) : "",
      row.source_role || "",
      line,
    ];
    if (withScore) cells.push(row.final_score != null ? String(Number(row.final_score).toFixed(2)) : "");
    cells.push(row.reason_code || "");
    return cells;
  });
}

function manifestRows(rows: readonly ManifestRow[]): string[][] {
  return rows.map((row) => [
    row.route_basename || "",
    row.source_role || "",
    (row.session_scope || []).join(","),
    row.final_score != null ? String(Number(row.final_score).toFixed(2)) : "",
    row.session_scope_score != null ? String(row.session_scope_score) : "",
    row.source_role_score != null ? String(row.source_role_score) : "",
    row.exact_title_match_score != null ? String(row.exact_title_match_score) : "",
  ]);
}

function QueryDetailBody({ detail }: { detail: TraceDetail }) {
  const rt = detail.retrieval.retrieval_trace_summary;
  const enh = detail.enhancement;

  return (
    <Stack gap={12}>
      <Callout tone={calloutTone(detail.quality.label)} title={`Quality: ${detail.quality.label}`}>
        status={detail.status} · format={detail.format}
        {detail.target_session != null ? ` · target_session=${detail.target_session}` : ""}
        {detail.quality.cited_sessions?.length
          ? ` · cited_sessions=[${detail.quality.cited_sessions.join(", ")}]`
          : ""}
      </Callout>

      <Grid columns={4} gap={12}>
        <Stat label="Admitted" value={String(detail.retrieval.admitted_count)} />
        <Stat label="Rejected" value={String(detail.retrieval.rejected_count)} />
        <Stat label="Citations" value={String(detail.citations.length)} />
        <Stat label="Model" value={detail.llm_model || "n/a"} />
      </Grid>

      <Text size="small" tone="secondary">
        Artifact: <Code>{detail.artifact_path}</Code>
      </Text>

      {enh?.source && (
        <>
          <H3>Query enhancement</H3>
          <Text size="small">source={enh.source}</Text>
          {enh.effective_question ? <MonoBlock value={enh.effective_question} /> : null}
        </>
      )}

      {detail.transition_rows.length > 0 && (
        <>
          <Divider />
          <H3>Pipeline</H3>
          <Table
            headers={["Step", "Input / artifact", "Processor", "Output / gate"]}
            rows={[...detail.transition_rows]}
            striped
          />
        </>
      )}

      {detail.retrieval.retrieval_query && (
        <>
          <Divider />
          <H3>Retrieval query</H3>
          <MonoBlock value={detail.retrieval.retrieval_query} />
        </>
      )}

      {rt && (
        <Grid columns={3} gap={12}>
          <Stat label="last/final" value={String(rt.asks_for_last_or_final)} />
          <Stat label="play_event" value={String(rt.asks_for_play_event)} />
          <Stat label="sessions" value={(rt.session_numbers || []).join(", ") || "n/a"} />
        </Grid>
      )}

      {rt?.top_manifest_entries?.length ? (
        <>
          <H3>Top manifest entries</H3>
          <Table
            headers={["route", "role", "sessions", "final", "scope+", "role+", "title+"]}
            rows={manifestRows(rt.top_manifest_entries)}
            striped
            stickyHeader
            style={{ maxHeight: 360 }}
          />
        </>
      ) : null}

      {detail.retrieval.top_admitted.length > 0 && (
        <>
          <H3>Top admitted evidence</H3>
          <Table
            headers={["id", "path", "sess", "role", "lines", "score", "reason"]}
            rows={evidenceRows(detail.retrieval.top_admitted, true)}
            striped
            stickyHeader
            style={{ maxHeight: 320 }}
          />
        </>
      )}

      {detail.retrieval.top_rejected.length > 0 && (
        <>
          <H3>Top rejected evidence</H3>
          <Table
            headers={["id", "path", "sess", "role", "lines", "score", "reason"]}
            rows={evidenceRows(detail.retrieval.top_rejected, true)}
            striped
            stickyHeader
            style={{ maxHeight: 280 }}
          />
        </>
      )}

      {detail.answer.text && (
        <>
          <Divider />
          <H3>Answer</H3>
          <MonoBlock value={detail.answer.text} />
        </>
      )}

      {detail.citations.length > 0 && (
        <>
          <H3>Citations</H3>
          <Table
            headers={["evidence_id", "path", "sess", "role", "lines", "reason"]}
            rows={evidenceRows(detail.citations, false)}
            striped
          />
        </>
      )}

      {detail.warnings.length > 0 && (
        <Callout tone="warning" title="Warnings">
          {detail.warnings.join("; ")}
        </Callout>
      )}
    </Stack>
  );
}

function QueryAccordionRow({ row }: { row: QueryRow }) {
  const s = row.summary;
  const headerTitle =
    s.target_session != null ? `Session ${s.target_session}: ${s.question}` : s.question;

  return (
    <Card collapsible defaultOpen={row.default_expanded}>
      <CardHeader
        trailing={
          <Row gap={8} align="center">
            <Pill tone={pillTone(s.quality_label)} size="sm">
              {s.quality_label}
            </Pill>
            <Text size="small" tone="tertiary">
              {s.admitted_count}a · {s.rejected_count}r · {s.citation_count}c
            </Text>
          </Row>
        }
      >
        {headerTitle}
      </CardHeader>
      <CardBody>
        <Stack gap={10}>
          <Text size="small" tone="secondary">
            {s.answer_preview}
          </Text>
          <Text size="small" tone="tertiary">
            <Code>{s.artifact_basename}</Code>
            {s.has_enhancement ? " · enhancement" : ""}
            {s.warnings.length ? ` · ${s.warnings.join(", ")}` : ""}
          </Text>
          <QueryDetailBody detail={row.detail} />
        </Stack>
      </CardBody>
    </Card>
  );
}

export default function LiveQueryTelemetryTraceSession22() {
  const [payload] = useCanvasState<CanvasPayload>("liveQueryTracePayload", EMPTY_PAYLOAD);
  const loaded = payload.queries.length > 0;

  return (
    <Stack gap={14} style={{ padding: 16 }}>
      <H1>Live Query Trace Review</H1>
      <Text tone="secondary">
        Canvas shell: <Code>{CANVAS_ID}</Code> · Data sidecar:{" "}
        <Code>{CANVAS_ID.replace(".canvas.tsx", ".canvas.data.json")}</Code>
      </Text>
      <Text tone="secondary">
        Refresh:{" "}
        <Code>
          uv run python -m evals.c2_live_prep.live_query_trace_canvas_emit --trace path.json:collapsed
          --trace path.json
        </Code>
      </Text>

      {!loaded && (
        <Callout tone="warning" title="No queries loaded">
          Run the emitter with one or more --trace artifacts, then reopen this canvas tab.
        </Callout>
      )}

      {payload.queries.map((row) => (
        <QueryAccordionRow key={row.query_id} row={row} />
      ))}
    </Stack>
  );
}
