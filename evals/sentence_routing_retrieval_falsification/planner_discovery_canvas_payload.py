"""Generate the planner discovery review canvas from report artifacts.

This script is the canonical way to regenerate:
`~/.cursor/projects/.../canvases/planner-discovery-review.canvas.tsx`

It builds a per-scenario expected-vs-actual payload from:
- planner discovery report JSON
- natural query gold JSON

Then writes a standalone `.canvas.tsx` file with inline data.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from evals.sentence_routing_retrieval_falsification.cursor_canvas_paths import default_cursor_canvas_path

_DEFAULT_PLANNER_DISCOVERY_CANVAS = default_cursor_canvas_path("planner-discovery-review.canvas.tsx")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_router_report(report: dict[str, Any]) -> bool:
    return str(report.get("harness") or "").startswith("breadcrumb_query_planner_router")


def _router_rows_by_scenario_id(router_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for raw in router_report.get("results") or []:
        if not isinstance(raw, dict):
            continue
        sid = str(raw.get("scenario_id") or "").strip()
        if sid:
            out[sid] = raw
    return out


def _merge_router_overlay_into_discovery_actual(
    actual: dict[str, Any],
    router_row: dict[str, Any],
) -> None:
    """Augment discovery ``actual`` with router + escalation fields from router harness."""
    actual["routerDecision"] = str(router_row.get("router_decision") or "")
    actual["routerFailureReasons"] = list(router_row.get("router_failure_reasons") or [])
    actual["escalationSkipped"] = bool(router_row.get("escalation_skipped"))

    payload = router_row.get("router_decision_payload") or {}
    esc_meta = payload.get("escalation") if isinstance(payload.get("escalation"), dict) else {}
    actual["routerSuggestedReadPaths"] = list(esc_meta.get("suggested_read_paths") or [])

    er = router_row.get("escalation_run")
    if isinstance(er, dict):
        actual["escalationPlannerReadPaths"] = list(er.get("planner_read_paths") or [])
        actual["escalationPlannerMessagePreview"] = str(er.get("planner_message_preview") or "")
        actual["escalationPlannerToolTrace"] = list(er.get("planner_tool_trace") or [])
        actual["escalationQuerySessionMemoryCallCount"] = int(
            er.get("query_session_memory_call_count") or 0
        )
        actual["escalationPlannerGrade"] = dict(er.get("planner_grade") or {})
    else:
        actual["escalationPlannerReadPaths"] = []
        actual["escalationPlannerMessagePreview"] = ""
        actual["escalationPlannerToolTrace"] = []
        actual["escalationQuerySessionMemoryCallCount"] = 0
        actual["escalationPlannerGrade"] = {}


def _row_payload_discovery(row: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    sid = str(row.get("scenario_id") or "")
    disc = row.get("planner_discovery") or {}
    return {
        "id": sid,
        "question": str(row.get("question") or ""),
        "expectedAnswer": str(scenario.get("expected_answer") or ""),
        "expected": {
            "mustHitTokens": list(scenario.get("must_hit_tokens") or []),
            "expectUnitIdSubstrings": list(scenario.get("expect_unit_id_substrings") or []),
            "expectRouteSubstrings": list(scenario.get("expect_route_substrings") or []),
            "expectedOpenPaths": list(disc.get("expected_open_paths") or []),
            "minContextSupportRatio": scenario.get("min_context_support_ratio"),
        },
        "actual": {
            "plannerReadPaths": list(disc.get("planner_read_paths") or []),
            "querySessionMemoryCallCount": int(disc.get("query_session_memory_call_count") or 0),
            "querySessionMemoryUnitIds": list(
                disc.get("planner_query_session_memory_unit_ids") or []
            ),
            "expectedOpenPathsCoverage": disc.get("expected_open_paths_coverage"),
            "expectedOpenPathsFullCoverage": disc.get("expected_open_paths_full_coverage"),
            "expectRouteCoverageOnReads": disc.get(
                "expect_route_substrings_coverage_on_reads"
            ),
            "benchmarkHitRouteCoverageOnReads": disc.get(
                "benchmark_hit_route_coverage_on_reads"
            ),
            "benchmarkRetrievalOk": bool(row.get("benchmark_retrieval_ok")),
            "benchmarkViolations": list(row.get("benchmark_violations") or []),
            "benchmarkGrade": dict(row.get("benchmark_grade") or {}),
            "plannerGrade": dict(row.get("planner_grade_vs_benchmark_retrieval") or {}),
            "plannerMessagePreview": str(row.get("planner_message_preview") or ""),
            "benchmarkLlmAnswerPreview": str(row.get("benchmark_llm_answer_preview") or ""),
            "plannerScenarioEstimatedCostUsd": row.get("planner_scenario_estimated_cost_usd"),
            "benchmarkLlmCostUsd": row.get("benchmark_llm_cost_usd"),
        },
    }


def _row_payload_router(row: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    sid = str(row.get("scenario_id") or "")
    escalation = row.get("escalation_run") or {}
    router_grade = row.get("router_grade") or {}
    planner_grade = escalation.get("planner_grade") or {}
    decision = str(row.get("router_decision") or "")
    failure_reasons = list(row.get("router_failure_reasons") or [])
    evidence = row.get("router_evidence_summary") or {}
    telemetry = row.get("scenario_telemetry_cost") or {}
    answered_now = decision == "answer_now"
    escalated = bool(row.get("escalation_run"))

    return {
        "id": sid,
        "question": str(row.get("question") or ""),
        "expectedAnswer": str(scenario.get("expected_answer") or ""),
        "expected": {
            "mustHitTokens": list(scenario.get("must_hit_tokens") or []),
            "expectUnitIdSubstrings": list(scenario.get("expect_unit_id_substrings") or []),
            "expectRouteSubstrings": list(scenario.get("expect_route_substrings") or []),
            "expectedOpenPaths": [],
            "minContextSupportRatio": scenario.get("min_context_support_ratio"),
        },
        "actual": {
            "routerDecision": decision,
            "routerFailureReasons": failure_reasons,
            "routerEvidence": dict(evidence),
            "routerRequiredAnchors": list(row.get("router_required_route_anchors") or []),
            "routerSynthCostUsd": row.get("router_synth_cost_usd"),
            "routerSynthAnswerPreview": str(row.get("router_synth_answer_preview") or ""),
            "routerGrade": dict(router_grade),
            "answeredNow": answered_now,
            "escalated": escalated,
            "escalationSkipped": bool(row.get("escalation_skipped")),
            "plannerReadPaths": list(escalation.get("planner_read_paths") or []),
            "querySessionMemoryCallCount": int(
                escalation.get("query_session_memory_call_count") or 0
            ),
            "querySessionMemoryUnitIds": list(
                escalation.get("planner_query_session_memory_unit_ids") or []
            ),
            "plannerGrade": dict(planner_grade),
            "plannerMessagePreview": str(escalation.get("planner_message_preview") or ""),
            "plannerScenarioEstimatedCostUsd": (
                (escalation.get("planner_telemetry_cost") or {}).get(
                    "scenario_estimated_cost_usd"
                )
                if escalation
                else None
            ),
            "scenarioEstimatedCostUsd": row.get("scenario_estimated_cost_usd"),
            "scenarioTelemetryCost": dict(telemetry),
            # Compatibility shims so the discovery-section components can render router rows too.
            "benchmarkRetrievalOk": False,
            "benchmarkViolations": [],
            "benchmarkGrade": {},
            "benchmarkLlmAnswerPreview": "",
            "benchmarkLlmCostUsd": None,
            "expectedOpenPathsCoverage": None,
            "expectedOpenPathsFullCoverage": None,
            "expectRouteCoverageOnReads": None,
            "benchmarkHitRouteCoverageOnReads": None,
        },
    }


def _build_router_summary(report: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    decision_counts = dict(report.get("decision_counts") or {})
    failure_reason_counts = dict(report.get("failure_reason_counts") or {})
    cohort_total = int(report.get("cohort_total") or len(rows))
    answer_now_pass = int(report.get("cohort_pass_count_answer_now") or 0)
    escalated_pass = int(report.get("cohort_pass_count_escalated") or 0)
    cohort_pass = int(
        report.get("cohort_pass_count")
        or (answer_now_pass + escalated_pass)
    )
    return {
        "scenarioCount": cohort_total,
        "plannerModel": report.get("planner_model"),
        "routerSynthModel": report.get("router_synth_model"),
        "noEscalation": bool(report.get("no_escalation")),
        "decisionCounts": decision_counts,
        "failureReasonCounts": failure_reason_counts,
        "answerNowCount": int(decision_counts.get("answer_now") or 0),
        "escalatedCount": int(decision_counts.get("need_more_context") or 0),
        "answerNowPassCount": answer_now_pass,
        "escalatedPassCount": escalated_pass,
        "cohortPassCount": cohort_pass,
        "aggregateRouterSynthCostUsd": report.get("aggregate_router_synth_cost_usd"),
        "aggregatePlannerCostUsd": report.get("aggregate_planner_cost_usd"),
        "aggregateScenarioCostUsd": report.get("aggregate_scenario_cost_usd"),
        "routerConfig": dict(report.get("router_config") or {}),
    }


def _build_discovery_summary(
    report: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    router_report_path: str | None = None,
) -> dict[str, Any]:
    aggregate = report.get("planner_discovery_aggregate") or {}
    out: dict[str, Any] = {
        "scenarioCount": len(rows),
        "plannerModel": report.get("planner_model"),
        "benchmarkModel": report.get("benchmark_llm_model"),
        "aggregatePlannerCostUsd": report.get("aggregate_scenario_planner_cost_usd"),
        "aggregateBenchmarkLlmCostUsd": report.get("aggregate_benchmark_llm_cost_usd"),
        "expectedOpenRecallMean": aggregate.get("expected_open_paths_recall_mean"),
        "expectedOpenFullCoverageScenarios": aggregate.get(
            "expected_open_paths_full_coverage_scenarios"
        ),
        "querySessionMemoryTotalCalls": aggregate.get("query_session_memory_total_calls"),
        "querySessionMemoryScenariosWithCalls": aggregate.get(
            "query_session_memory_scenarios_with_calls"
        ),
        "plannerGradePassCount": sum(
            1 for r in rows if bool((r.get("actual") or {}).get("plannerGrade", {}).get("ok"))
        ),
        "benchmarkRetrievalPassCount": sum(
            1 for r in rows if bool((r.get("actual") or {}).get("benchmarkRetrievalOk"))
        ),
    }
    if router_report_path:
        out["routerReportSource"] = router_report_path
        need_more = sum(
            1
            for r in rows
            if str((r.get("actual") or {}).get("routerDecision") or "") == "need_more_context"
        )
        # Escalation ran when router harness recorded corpus reads or a tool trace.
        escalated_ran = sum(
            1
            for r in rows
            if str((r.get("actual") or {}).get("routerDecision") or "") == "need_more_context"
            and (
                bool((r.get("actual") or {}).get("escalationPlannerReadPaths"))
                or bool((r.get("actual") or {}).get("escalationPlannerToolTrace"))
            )
        )
        skipped = sum(
            1
            for r in rows
            if str((r.get("actual") or {}).get("routerDecision") or "") == "need_more_context"
            and bool((r.get("actual") or {}).get("escalationSkipped"))
        )
        out["routerNeedMoreContextCount"] = need_more
        out["routerEscalationRanCount"] = escalated_ran
        out["routerEscalationSkippedCount"] = skipped
    return out


def build_payload(
    report: dict[str, Any],
    gold: dict[str, Any],
    *,
    router_report: dict[str, Any] | None = None,
    router_report_path: str | None = None,
) -> dict[str, Any]:
    scenarios_by_id = {str(s.get("id") or ""): s for s in (gold.get("scenarios") or [])}
    is_router = _is_router_report(report)
    rows: list[dict[str, Any]] = []
    router_by_id: dict[str, dict[str, Any]] = {}
    if not is_router and router_report is not None:
        router_by_id = _router_rows_by_scenario_id(router_report)

    for row in report.get("results") or []:
        sid = str(row.get("scenario_id") or "")
        scenario = scenarios_by_id.get(sid, {})
        if is_router:
            rows.append(_row_payload_router(row, scenario))
        else:
            payload_row = _row_payload_discovery(row, scenario)
            rr = router_by_id.get(sid)
            if rr is not None:
                _merge_router_overlay_into_discovery_actual(payload_row["actual"], rr)
            rows.append(payload_row)

    if is_router:
        summary = _build_router_summary(report, rows)
        title = "Planner Retrieval Router Review"
        subtitle = (
            "Per-query router decisions, escalation reasons, "
            "answer_now vs escalated outcomes, and cost split."
        )
    else:
        summary = _build_discovery_summary(
            report, rows, router_report_path=router_report_path or None
        )
        title = "Planner Query Discovery Review"
        subtitle = "Expected vs actual per-query metrics, planner reads, and LLM outputs."
        if router_report_path:
            subtitle += (
                " Includes router benchmark overlay (answer_now vs need_more_context) "
                "and escalation read/tool traces when present."
            )

    router_harness_meta: dict[str, Any] | None = None
    if router_report is not None:
        router_harness_meta = {
            "harness": str(router_report.get("harness") or ""),
            "no_escalation": bool(router_report.get("no_escalation")),
        }

    payload = {
        "title": title,
        "subtitle": subtitle,
        "harnessKind": "router" if is_router else "discovery",
        "sources": {
            "report": str(report.get("source_report_path") or ""),
            "gold": str(report.get("source_gold_path") or ""),
            "plannerDiscoveryGold": str(report.get("planner_discovery_gold") or ""),
            "routerReport": router_report_path or "",
        },
        "summary": summary,
        "rows": rows,
        "routerHarnessMeta": router_harness_meta,
    }
    return payload


def render_canvas_tsx(payload: dict[str, Any]) -> str:
    dumped = json.dumps(payload, ensure_ascii=True, indent=2)
    return f"""import {{
  Callout,
  Code,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  useHostTheme,
}} from 'cursor/canvas';

const canvasData = {dumped} as const;

const isRouter = (canvasData as any).harnessKind === 'router';

function PreBlock({{ text }}: {{ text: string }}) {{
  const theme = useHostTheme();
  return (
    <pre
      style={{{{
        margin: 0,
        whiteSpace: 'pre-wrap',
        overflowWrap: 'anywhere',
        border: `1px solid ${{theme.stroke.tertiary}}`,
        background: theme.fill.quaternary,
        color: theme.text.primary,
        borderRadius: 8,
        padding: 12,
        fontSize: 12,
        lineHeight: 1.45,
      }}}}
    >
      {{text || '—'}}
    </pre>
  );
}}

function toolTraceBlock(trace: any[] | undefined): string {{
  if (!trace || !trace.length) return '—';
  return trace
    .map((t: any) => {{
      const path = t.path ? ` path=${{t.path}}` : '';
      return `[${{t.tool || '?'}}]${{path}}\\n${{t.output_preview || ''}}`;
    }})
    .join('\\n---\\n');
}}

function metricRowsDiscovery(row: any): Array<[string, string, string]> {{
  const a = row.actual || {{}};
  const e = row.expected || {{}};
  const b = a.benchmarkGrade || {{}};
  const p = a.plannerGrade || {{}};
  const open = a.expectedOpenPathsCoverage || {{}};
  const route = a.expectRouteCoverageOnReads || {{}};
  const hit = a.benchmarkHitRouteCoverageOnReads || {{}};
  const rows: Array<[string, string, string]> = [
    ['Expected open-path recall', '1.0', String(open.recall ?? 'n/a')],
    ['Expected open full-coverage', 'true', String(a.expectedOpenPathsFullCoverage)],
    ['Expected route coverage on reads', '1.0', String(route.recall ?? 'n/a')],
    ['Benchmark-hit route coverage on reads', 'diagnostic', String(hit.recall ?? 'n/a')],
    ['Benchmark retrieval gate', 'true', String(a.benchmarkRetrievalOk)],
    ['Planner grade gate', 'true', String(p.ok)],
    [
      'Min context support ratio',
      String(e.minContextSupportRatio ?? 'n/a'),
      `benchmark=${{String(b.llm_context_support_ratio ?? b.context_support_ratio ?? 'n/a')}} | planner=${{String(p.llm_context_support_ratio ?? 'n/a')}}`,
    ],
    ['query_session_memory calls', 'optional', String(a.querySessionMemoryCallCount ?? 0)],
    [
      'Scenario cost (USD)',
      'diagnostic',
      `planner=${{String(a.plannerScenarioEstimatedCostUsd ?? 'n/a')}} | benchmark_llm=${{String(a.benchmarkLlmCostUsd ?? 'n/a')}}`,
    ],
  ];
  const rd = String(a.routerDecision || '');
  if (rd) {{
    rows.push(
      ['Router decision (harness overlay)', 'artifact', rd],
      ['Router failure reasons', 'none if empty', (a.routerFailureReasons || []).join(', ') || 'none'],
      ['Escalation skipped', 'false', String(Boolean(a.escalationSkipped))],
      ['Escalation QSM calls', 'optional', String(a.escalationQuerySessionMemoryCallCount ?? 0)],
    );
  }}
  return rows;
}}

function metricRowsRouter(row: any): Array<[string, string, string]> {{
  const a = row.actual || {{}};
  const e = row.expected || {{}};
  const r = a.routerGrade || {{}};
  const p = a.plannerGrade || {{}};
  const ev = a.routerEvidence || {{}};
  const tc = a.scenarioTelemetryCost || {{}};
  return [
    ['Router decision', 'answer_now (when sufficient)', String(a.routerDecision || 'n/a')],
    [
      'Router failure reasons',
      'none on answer_now',
      (a.routerFailureReasons || []).join(', ') || 'none',
    ],
    ['Top hit score', '>= cfg.min_top_hit_score', String(ev.top_hit_score ?? 'n/a')],
    ['Matched records', '>= cfg.min_matched_records', String(ev.matched_records ?? 'n/a')],
    ['Returned hits', '>= cfg.min_hits', String(ev.returned_hits ?? 'n/a')],
    ['Context density', '>= cfg.min_context_density', String(ev.context_density ?? 'n/a')],
    ['Route anchor recall', 'cfg.min_route_anchor_recall', String(ev.route_anchor_recall ?? 'n/a')],
    ['Expansion fill ratio', '<= cfg.max_expansion_fill_ratio', String(ev.expansion_fill_ratio ?? 'n/a')],
    ['Router grade gate', 'true', String(r.ok ?? 'n/a')],
    ['Escalated planner grade gate', 'true', String(p.ok ?? 'n/a')],
    [
      'Min context support ratio',
      String(e.minContextSupportRatio ?? 'n/a'),
      `router=${{String(r.llm_context_support_ratio ?? r.context_support_ratio ?? 'n/a')}} | planner=${{String(p.llm_context_support_ratio ?? p.context_support_ratio ?? 'n/a')}}`,
    ],
    [
      'Cost split (USD)',
      'diagnostic',
      `router_synth=${{String(a.routerSynthCostUsd ?? '0')}} | planner=${{String(a.plannerScenarioEstimatedCostUsd ?? '0')}} | scenario_total=${{String(tc.scenario_estimated_cost_usd ?? a.scenarioEstimatedCostUsd ?? 'n/a')}}`,
    ],
    ['query_session_memory calls (escalation)', 'optional', String(a.querySessionMemoryCallCount ?? 0)],
  ];
}}

function metricRows(row: any): Array<[string, string, string]> {{
  return isRouter ? metricRowsRouter(row) : metricRowsDiscovery(row);
}}

function ScenarioSection({{ row }}: {{ row: any }}) {{
  const a = row.actual || {{}};
  const p = a.plannerGrade || {{}};
  const b = a.benchmarkGrade || {{}};
  const r = a.routerGrade || {{}};
  const pPass = Boolean(p.ok);
  const bPass = Boolean(a.benchmarkRetrievalOk);
  const rPass = Boolean(r.ok);
  const decision = String(a.routerDecision || '');
  const escalated = Boolean(a.escalated);
  return (
    <Stack gap={{10}}>
      <Row gap={{8}} align="center" wrap>
        <Code>{{row.id}}</Code>
        {{isRouter ? (
          <>
            <Pill tone={{decision === 'answer_now' ? 'success' : 'warning'}}>
              router: {{decision || 'n/a'}}
            </Pill>
            {{decision === 'answer_now' && (
              <Pill tone={{rPass ? 'success' : 'warning'}}>router_grade: {{rPass ? 'PASS' : 'FAIL'}}</Pill>
            )}}
            {{escalated && (
              <Pill tone={{pPass ? 'success' : 'warning'}}>escalated_planner_grade: {{pPass ? 'PASS' : 'FAIL'}}</Pill>
            )}}
          </>
        ) : (
          <>
            <Pill tone={{bPass ? 'success' : 'warning'}}>benchmark_retrieval: {{bPass ? 'PASS' : 'FAIL'}}</Pill>
            <Pill tone={{pPass ? 'success' : 'warning'}}>planner_grade: {{pPass ? 'PASS' : 'FAIL'}}</Pill>
            {{Boolean(a.routerDecision) && (
              <Pill
                tone={{
                  a.routerDecision === 'need_more_context'
                    ? 'warning'
                    : a.routerDecision === 'answer_now'
                      ? 'success'
                      : 'neutral'
                }}
              >
                router: {{a.routerDecision}}
              </Pill>
            )}}
          </>
        )}}
      </Row>
      <Text>{{row.question}}</Text>

      <Grid columns={{2}} gap={{14}}>
        <Stack gap={{8}}>
          <H3>Expected</H3>
          <Text tone="secondary" size="small">Must-hit tokens</Text>
          <PreBlock text={{(row.expected?.mustHitTokens || []).join(', ') || '—'}} />
          <Text tone="secondary" size="small">Expected unit id substrings</Text>
          <PreBlock text={{(row.expected?.expectUnitIdSubstrings || []).join(', ') || '—'}} />
          <Text tone="secondary" size="small">Expected route substrings</Text>
          <PreBlock text={{(row.expected?.expectRouteSubstrings || []).join(', ') || '—'}} />
          {{!isRouter && (
            <>
              <Text tone="secondary" size="small">Expected open paths (planner discovery gold)</Text>
              <PreBlock text={{(row.expected?.expectedOpenPaths || []).join('\\n') || '—'}} />
            </>
          )}}
          {{isRouter && (
            <>
              <Text tone="secondary" size="small">Router required route anchors</Text>
              <PreBlock text={{(a.routerRequiredAnchors || []).join('\\n') || '—'}} />
            </>
          )}}
          <Text tone="secondary" size="small">Expected answer (gold)</Text>
          <PreBlock text={{row.expectedAnswer || '—'}} />
        </Stack>

        <Stack gap={{8}}>
          <H3>Actual</H3>
          <Table headers={{['Metric', 'Expected', 'Actual']}} rows={{metricRows(row)}} />
          <Text tone="secondary" size="small">Planner read paths{{isRouter ? ' (escalation)' : ''}}</Text>
          <PreBlock text={{(a.plannerReadPaths || []).join('\\n') || '—'}} />
          {{!isRouter && Boolean(a.routerDecision) && (
            <>
              <Text tone="secondary" size="small">Router suggested read paths (telemetry overlay)</Text>
              <PreBlock text={{(a.routerSuggestedReadPaths || []).join('\\n') || '—'}} />
              <Text tone="secondary" size="small">Escalation planner read paths (after need_more_context)</Text>
              <PreBlock text={{(a.escalationPlannerReadPaths || []).join('\\n') || '—'}} />
              <Text tone="secondary" size="small">Escalation tool trace (tool + path + output preview)</Text>
              <PreBlock text={{toolTraceBlock(a.escalationPlannerToolTrace)}} />
            </>
          )}}
          {{isRouter ? (
            <>
              <Text tone="secondary" size="small">Router violations</Text>
              <PreBlock text={{(r.violations || []).join(', ') || 'none'}} />
              {{escalated && (
                <>
                  <Text tone="secondary" size="small">Escalated planner violations</Text>
                  <PreBlock text={{(p.violations || []).join(', ') || 'none'}} />
                </>
              )}}
              <Text tone="secondary" size="small">Semantic verdicts</Text>
              <PreBlock text={{`router=${{String(r.llm_semantic_verdict ?? r.semantic_verdict ?? 'n/a')}} | planner=${{String(p.llm_semantic_verdict ?? p.semantic_verdict ?? 'n/a')}}`}} />
            </>
          ) : (
            <>
              <Text tone="secondary" size="small">Benchmark violations</Text>
              <PreBlock text={{(a.benchmarkViolations || []).join(', ') || 'none'}} />
              <Text tone="secondary" size="small">Planner violations</Text>
              <PreBlock text={{(p.violations || []).join(', ') || 'none'}} />
              <Text tone="secondary" size="small">Semantic verdicts</Text>
              <PreBlock text={{`benchmark=${{String(b.llm_semantic_verdict ?? b.semantic_verdict ?? 'n/a')}} | planner=${{String(p.llm_semantic_verdict ?? 'n/a')}}`}} />
            </>
          )}}
        </Stack>
      </Grid>

      <Grid columns={{2}} gap={{14}}>
        {{isRouter ? (
          <>
            <Stack gap={{8}}>
              <H3>Router answer-now LLM Response</H3>
              <PreBlock text={{a.routerSynthAnswerPreview || '—'}} />
            </Stack>
            <Stack gap={{8}}>
              <H3>Escalated Planner LLM Response</H3>
              <PreBlock text={{a.plannerMessagePreview || (a.escalationSkipped ? '(escalation skipped via --no-escalation)' : '—')}} />
            </Stack>
          </>
        ) : (
          <>
            <Stack gap={{8}}>
              <H3>Benchmark LLM Response</H3>
              <PreBlock text={{a.benchmarkLlmAnswerPreview || '—'}} />
            </Stack>
            <Stack gap={{8}}>
              <H3>Planner LLM Response (discovery harness)</H3>
              <PreBlock text={{a.plannerMessagePreview || '—'}} />
            </Stack>
          </>
        )}}
      </Grid>
      {{!isRouter && Boolean(a.routerDecision) && (
        <Stack gap={{8}}>
          <H3>Escalation planner LLM Response (router harness)</H3>
          <PreBlock
            text={{
              a.escalationPlannerMessagePreview ||
                (a.escalationSkipped ? '(escalation skipped — router run used --no-escalation)' : '—')
            }}
          />
        </Stack>
      )}}
      <Divider />
    </Stack>
  );
}}

function discoverySummaryRows(rows: any[], withRouter: boolean): any[][] {{
  return rows.map((row: any) => {{
    const a = row.actual || {{}};
    const p = a.plannerGrade || {{}};
    const base = [
      <Code>{{row.id}}</Code>,
      String(a.benchmarkRetrievalOk),
      String(p.ok),
      String(a.expectedOpenPathsCoverage?.recall ?? 'n/a'),
      String(a.querySessionMemoryCallCount ?? 0),
      String(a.plannerScenarioEstimatedCostUsd ?? 'n/a'),
      (p.violations || []).join(', ') || 'none',
    ];
    if (!withRouter) return base;
    const traces = a.escalationPlannerToolTrace || [];
    return [
      ...base,
      String(a.routerDecision || '—'),
      String((a.escalationPlannerReadPaths || []).length),
      String(traces.length),
    ];
  }});
}}

function NeedMoreContextEscalations({{ rows }}: {{ rows: any[] }}) {{
  const xs = (rows || []).filter(
    (row: any) => String(row.actual?.routerDecision || '') === 'need_more_context',
  );
  if (!xs.length) return null;
  return (
    <Stack gap={{14}}>
      <H2>{{'Router: need_more_context (' + String(xs.length) + ' scenarios)'}}</H2>
      <Text tone="secondary" size="small">
        Suggested read paths from router telemetry, plus escalation planner corpus reads and tool-trace previews when the router harness ran a full planner turn.
      </Text>
      {{xs.map((row: any) => {{
        const a = row.actual || {{}};
        return (
          <Stack key={{row.id}} gap={{8}}>
            <Row gap={{8}} align="center" wrap>
              <Code>{{row.id}}</Code>
              {{a.escalationSkipped ? <Pill tone="warning">escalation_skipped</Pill> : null}}
            </Row>
            <Text size="small">{{row.question}}</Text>
            <Text tone="secondary" size="small">Router suggested read paths</Text>
            <PreBlock text={{(a.routerSuggestedReadPaths || []).join('\\n') || '—'}} />
            <Text tone="secondary" size="small">Escalation planner read paths</Text>
            <PreBlock text={{(a.escalationPlannerReadPaths || []).join('\\n') || '—'}} />
            <Text tone="secondary" size="small">Escalation tool trace</Text>
            <PreBlock text={{toolTraceBlock(a.escalationPlannerToolTrace)}} />
            <Text tone="secondary" size="small">Escalation message preview</Text>
            <PreBlock text={{a.escalationPlannerMessagePreview || '—'}} />
            <Divider />
          </Stack>
        );
      }})}}
    </Stack>
  );
}}

function routerSummaryRows(rows: any[]): any[][] {{
  return rows.map((row: any) => {{
    const a = row.actual || {{}};
    const r = a.routerGrade || {{}};
    const p = a.plannerGrade || {{}};
    const decision = String(a.routerDecision || '');
    const tc = a.scenarioTelemetryCost || {{}};
    return [
      <Code>{{row.id}}</Code>,
      decision,
      decision === 'answer_now' ? String(r.ok ?? 'n/a') : 'n/a',
      a.escalated ? String(p.ok ?? 'n/a') : 'n/a',
      (a.routerFailureReasons || []).join(', ') || 'none',
      String(tc.scenario_estimated_cost_usd ?? a.scenarioEstimatedCostUsd ?? 'n/a'),
      (p.violations || r.violations || []).join(', ') || 'none',
    ];
  }});
}}

function failureReasonRows(counts: Record<string, number>): any[][] {{
  return Object.entries(counts || {{}}).map(([k, v]) => [k, String(v)]);
}}

export default function PlannerDiscoveryReview() {{
  const d: any = canvasData;
  const s = d.summary || {{}};
  const hasRouterOverlay = Boolean(s.routerReportSource);
  const rhm = d.routerHarnessMeta || {{}};
  const summaryRows = isRouter
    ? routerSummaryRows(d.rows || [])
    : discoverySummaryRows(d.rows || [], hasRouterOverlay);

  return (
    <Stack gap={{20}}>
      <Stack gap={{8}}>
        <H1>{{d.title}}</H1>
        <Text>{{d.subtitle}}</Text>
        <Text tone="secondary" size="small">Report: <Code>{{d.sources.report}}</Code></Text>
        <Text tone="secondary" size="small">Gold: <Code>{{d.sources.gold}}</Code></Text>
        {{!isRouter && (
          <Text tone="secondary" size="small">Planner discovery gold: <Code>{{d.sources.plannerDiscoveryGold}}</Code></Text>
        )}}
        {{hasRouterOverlay && (
          <Text tone="secondary" size="small">Router overlay report: <Code>{{d.sources.routerReport}}</Code></Text>
        )}}
      </Stack>

      {{isRouter ? (
        <>
          <Grid columns={{5}} gap={{12}}>
            <Stat value={{`${{s.cohortPassCount}}/${{s.scenarioCount}}`}} label="Cohort pass (router or escalated)" tone="warning" />
            <Stat value={{`${{s.answerNowCount}}/${{s.scenarioCount}}`}} label="answer_now decisions" />
            <Stat value={{`${{s.answerNowPassCount}}/${{s.answerNowCount || 0}}`}} label="answer_now pass" tone="warning" />
            <Stat value={{`${{s.escalatedCount}}/${{s.scenarioCount}}`}} label="need_more_context decisions" />
            <Stat value={{`${{s.escalatedPassCount}}/${{s.escalatedCount || 0}}`}} label="escalated pass" tone="warning" />
            <Stat value={{`$${{Number(s.aggregateRouterSynthCostUsd || 0).toFixed(4)}}`}} label="Aggregate router synth cost" />
            <Stat value={{`$${{Number(s.aggregatePlannerCostUsd || 0).toFixed(4)}}`}} label="Aggregate planner escalation cost" />
            <Stat value={{`$${{Number(s.aggregateScenarioCostUsd || 0).toFixed(4)}}`}} label="Aggregate scenario cost" />
            <Stat value={{s.plannerModel || 'n/a'}} label="Planner model" />
            <Stat value={{s.routerSynthModel || 'n/a'}} label="Router synth model" />
          </Grid>

          <Callout tone="neutral" title="Router decision distribution">
            <Stack gap={{6}}>
              <Text size="small">{{`answer_now: ${{s.answerNowCount || 0}} | need_more_context: ${{s.escalatedCount || 0}} | no_escalation_flag: ${{String(s.noEscalation)}}`}}</Text>
              <Text tone="secondary" size="small">Router config (sufficiency thresholds)</Text>
              <PreBlock text={{JSON.stringify(s.routerConfig || {{}}, null, 2)}} />
            </Stack>
          </Callout>

          <H2>Failure Reasons</H2>
          <Table headers={{['Reason', 'Count']}} rows={{failureReasonRows(s.failureReasonCounts || {{}})}} />
        </>
      ) : (
        <>
          <Grid columns={{5}} gap={{12}}>
            <Stat value={{`${{s.plannerGradePassCount}}/${{s.scenarioCount}}`}} label="Planner grade pass" tone="warning" />
            <Stat value={{`${{s.benchmarkRetrievalPassCount}}/${{s.scenarioCount}}`}} label="Benchmark retrieval pass" tone="warning" />
            <Stat value={{`$${{Number(s.aggregatePlannerCostUsd || 0).toFixed(4)}}`}} label="Aggregate planner cost" />
            <Stat value={{`$${{Number(s.aggregateBenchmarkLlmCostUsd || 0).toFixed(4)}}`}} label="Aggregate benchmark LLM cost" />
            <Stat value={{String(s.expectedOpenRecallMean ?? 'n/a')}} label="Mean expected-open recall" tone="warning" />
            <Stat value={{`${{s.expectedOpenFullCoverageScenarios}}/${{s.scenarioCount}}`}} label="Full expected-open coverage" tone="warning" />
            <Stat value={{String(s.querySessionMemoryTotalCalls ?? '0')}} label="query_session_memory calls" />
            <Stat value={{`${{s.querySessionMemoryScenariosWithCalls}}/${{s.scenarioCount}}`}} label="Scenarios with qsm" />
            <Stat value={{s.plannerModel || 'n/a'}} label="Planner model" />
            <Stat value={{s.benchmarkModel || 'n/a'}} label="Benchmark synthesis model" />
          </Grid>

          {{hasRouterOverlay && (
            <Grid columns={{4}} gap={{12}}>
              <Stat
                value={{`${{s.routerNeedMoreContextCount}}/${{s.scenarioCount}}`}}
                label="Router need_more_context"
                tone="warning"
              />
              <Stat
                value={{`${{s.routerEscalationRanCount}}/${{s.routerNeedMoreContextCount || 0}}`}}
                label="Escalations with reads or tool trace"
                tone="warning"
              />
              <Stat value={{String(s.routerEscalationSkippedCount ?? 0)}} label="Escalation skipped rows" />
              <Stat value={{String(rhm.harness || 'n/a')}} label="Router harness (overlay)" />
            </Grid>
          )}}

          {{hasRouterOverlay && Boolean(rhm.no_escalation) && (
            <Callout tone="warning" title="Router overlay: planner escalation was not run">
              <Text size="small">
                This router report was produced with <Code>--no-escalation</Code>. Rows with
                <Code>need_more_context</Code> will not show escalation read paths or tool output. Re-run the router
                harness without that flag and pass <Code>--router-report</Code> again when regenerating this canvas.
              </Text>
            </Callout>
          )}}

          <Callout tone="neutral" title="Expected vs actual by query">
            Expected values come from natural benchmark gold plus planner-discovery gold. Actual values come
            from live planner traces and graded outputs for each query, including both benchmark and planner
            LLM responses.
          </Callout>

          {{hasRouterOverlay && <NeedMoreContextEscalations rows={{d.rows || []}} />}}
        </>
      )}}

      <H2>Scenario Matrix</H2>
      {{isRouter ? (
        <Table
          headers={{
            [
              'Scenario',
              'router_decision',
              'router_grade_ok',
              'escalated_planner_grade_ok',
              'router_failure_reasons',
              'scenario_cost_usd',
              'violations',
            ]
          }}
          rows={{summaryRows}}
        />
      ) : hasRouterOverlay ? (
        <Table
          headers={{
            [
              'Scenario',
              'benchmark_retrieval_ok',
              'planner_grade_ok',
              'expected_open_recall',
              'qsm_calls',
              'planner_cost_usd',
              'planner_violations',
              'router_decision',
              'escal_read_paths_n',
              'escal_tool_trace_n',
            ]
          }}
          rows={{summaryRows}}
        />
      ) : (
        <Table
          headers={{
            [
              'Scenario',
              'benchmark_retrieval_ok',
              'planner_grade_ok',
              'expected_open_recall',
              'qsm_calls',
              'planner_cost_usd',
              'planner_violations',
            ]
          }}
          rows={{summaryRows}}
        />
      )}}

      <Divider />

      <H2>Per-Query Expected vs Actual</H2>
      <Stack gap={{18}}>
        {{(d.rows || []).map((row: any) => (
          <ScenarioSection key={{row.id}} row={{row}} />
        ))}}
      </Stack>
    </Stack>
  );
}}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument(
        "--router-report",
        type=Path,
        default=None,
        help=(
            "Optional planner-router harness JSON; merged into discovery rows "
            "(router decision, suggested reads, escalation reads/tool trace)."
        ),
    )
    parser.add_argument(
        "--canvas-tsx",
        type=Path,
        default=_DEFAULT_PLANNER_DISCOVERY_CANVAS,
        help=(
            "Output .canvas.tsx path. "
            f"Default: Cursor-managed {_DEFAULT_PLANNER_DISCOVERY_CANVAS} "
            "(set DMB_CURSOR_CANVAS_DIR to override the parent canvases/ dir)."
        ),
    )
    args = parser.parse_args()

    report = _load_json(args.report.resolve())
    gold = _load_json(args.gold.resolve())
    report["source_report_path"] = str(args.report.resolve())
    report["source_gold_path"] = str(args.gold.resolve())
    router_report: dict[str, Any] | None = None
    router_path_str: str | None = None
    if args.router_report is not None:
        rp = args.router_report.resolve()
        router_report = _load_json(rp)
        router_path_str = str(rp)
    payload = build_payload(
        report,
        gold,
        router_report=router_report,
        router_report_path=router_path_str,
    )
    text = render_canvas_tsx(payload)

    args.canvas_tsx.parent.mkdir(parents=True, exist_ok=True)
    args.canvas_tsx.write_text(text, encoding="utf-8")
    print(json.dumps({"wrote": str(args.canvas_tsx.resolve())}, indent=2))


if __name__ == "__main__":
    main()
