import {
  Callout,
  Card,
  CardBody,
  CardHeader,
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
} from 'cursor/canvas';

const fullCohortPath =
  'evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-30/sentence_routing_stage_b_discourse_pipeline_summary--sentence_routing_c2_session20_pc--gpt-5.4-mini--N5--20260430T033552Z.json';

const edgeCohortPath =
  'evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-30/sentence_routing_stage_b_discourse_pipeline_summary--sentence_routing_c2_session20_pc_edge_slice_h1_h2_sentinel--gpt-5.4-mini--N5--20260430T033703Z.json';

export default function StageBContractHardeningStatus() {
  return (
    <Stack gap={20}>
      <Stack gap={8}>
        <Row gap={8} wrap>
          <Pill tone="success" active>Cleaned Up</Pill>
          <Pill tone="info" active>67 Tests Passing</Pill>
          <Pill tone="warning" active>Benchmarks Still Gate-Fail</Pill>
        </Row>
        <H1>Stage B Contract Hardening Status</H1>
        <Text tone="secondary">
          Current state after cleanup: contract integrity is materially stronger, gold migration is
          falsified as invariant, and benchmark cost is flat. The remaining failures are benchmark
          behavior, not cleanup regressions.
        </Text>
      </Stack>

      <Grid columns={4} gap={16}>
        <Stat value="67/67" label="Focused tests" tone="success" />
        <Stat value="0/5" label="Full C2 pass rate" tone="warning" />
        <Stat value="2/5" label="H1/H2 edge pass rate" tone="info" />
        <Stat value="$0.249" label="Full C2 N=5 cost" />
      </Grid>

      <Callout tone="success" title="Main conclusion">
        The cleanup did not introduce a cost regression. Full C2 remains failing, but the failure
        profile is now better instrumented: preflight is enforced, capture drift is checked, and
        B2 coherence corrections are visible in sidecars.
      </Callout>

      <Divider />

      <H2>What Is Done</H2>
      <Table
        headers={['Area', 'Status', 'Evidence']}
        rows={[
          [
            'Gold migration',
            'Invariant',
            'Current unit_id gold and derived legacy match gold produced identical B2 violations on the same saved B1 sidecar.',
          ],
          [
            'Capture signature',
            'Enforced',
            'expected_capture_signature is stamped into both C2 Session 20 scenarios and checked during preflight.',
          ],
          [
            'Preflight coverage',
            'Broadened',
            'step2_route, step2_discourse_pipeline, step2a_discourse, and step2b_from_discourse now run preflight.',
          ],
          [
            'Coherence seam',
            'Moved',
            'Normalization now runs on discourse rows before reduction and emits b2_coherence_corrections.',
          ],
          [
            'Telemetry naming',
            'Cleaned',
            'b3_correction_events was replaced with b2_coherence_corrections to avoid implying a B3 stage exists.',
          ],
        ]}
        rowTone={['success', 'success', 'success', 'success', 'success']}
      />

      <H2>Benchmark Snapshot</H2>
      <Grid columns="1fr 1fr" gap={16}>
        <Card>
          <CardHeader trailing={<Pill tone="warning" size="sm">Gate Fail</Pill>}>
            Full C2 Session 20 N=5
          </CardHeader>
          <CardBody>
            <Stack gap={12}>
              <Grid columns={3} gap={12}>
                <Stat value="0/5" label="Passes" tone="warning" />
                <Stat value="$0.248994" label="Cost sum" />
                <Stat value="4" label="Coherence corrections" tone="info" />
              </Grid>
              <Text size="small" tone="secondary">
                Buckets: b1_missing_expected_hub=15, b1_over_route=2, b2_over_assigned=5.
              </Text>
              <Text size="small">
                Artifact: <Code>{fullCohortPath}</Code>
              </Text>
            </Stack>
          </CardBody>
        </Card>

        <Card>
          <CardHeader trailing={<Pill tone="info" size="sm">Improved</Pill>}>
            H1/H2 Sentinel Edge N=5
          </CardHeader>
          <CardBody>
            <Stack gap={12}>
              <Grid columns={3} gap={12}>
                <Stat value="2/5" label="Passes" tone="info" />
                <Stat value="$0.031762" label="Cost sum" />
                <Stat value="7" label="Coherence corrections" tone="info" />
              </Grid>
              <Text size="small" tone="secondary">
                Buckets: b1_missing_expected_hub=1; B1 content topic_pc_slugs mismatch=1.
              </Text>
              <Text size="small">
                Artifact: <Code>{edgeCohortPath}</Code>
              </Text>
            </Stack>
          </CardBody>
        </Card>
      </Grid>

      <H2>Cost Comparison</H2>
      <Table
        headers={['Cohort', 'Runs', 'Passes', 'Mean Cost', 'Sum Cost', 'Cost Read']}
        rows={[
          ['Prior full C2', '3', '0', '$0.047353', '$0.142060', 'Earlier baseline, no preflight metadata'],
          ['Pre-cleanup full C2', '5', '0', '$0.049756', '$0.248778', 'Reference for cleanup regression check'],
          ['Post-cleanup full C2', '5', '0', '$0.049799', '$0.248994', 'Flat vs pre-cleanup N=5'],
          ['Prior H1/H2 edge A', '5', '1', '$0.006574', '$0.032872', 'Prior edge baseline'],
          ['Prior H1/H2 edge B', '5', '0', '$0.006205', '$0.031024', 'Prior edge baseline'],
          ['Post-cleanup H1/H2 edge', '5', '2', '$0.006352', '$0.031762', 'Within prior envelope'],
        ]}
        rowTone={[undefined, undefined, 'success', undefined, undefined, 'success']}
        columnAlign={['left', 'right', 'right', 'right', 'right', 'left']}
      />

      <Divider />

      <H2>Remaining Risk</H2>
      <Grid columns="1.2fr 1fr" gap={16}>
        <Stack gap={10}>
          <H3>Not solved yet</H3>
          <Text>
            Full C2 still fails all five runs. The cleanup clarified attribution, but it did not
            make the large scenario pass. Current failures are dominated by B1 state gaps and
            over-routing in B1-derived expectations.
          </Text>
          <Text>
            The coherence normalizer is now real and visible, but it is not a gold-aware repair
            stage. That is intentional: it only removes deterministic contradictions before
            grading.
          </Text>
        </Stack>
        <Card>
          <CardHeader>Next Decision</CardHeader>
          <CardBody>
            <Text>
              Decide whether the residual full-C2 buckets justify prompt work in B1, more
              deterministic discourse normalization, or a narrow post-reducer B3. The edge slice
              improved, so the next move should be bucket-driven rather than broad refactoring.
            </Text>
          </CardBody>
        </Card>
      </Grid>
    </Stack>
  );
}
