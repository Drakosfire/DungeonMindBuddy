import { Callout, Card, CardBody, CardHeader, Code, Divider, Grid, H1, H2, H3, Pill, Row, Stack, Stat, Table, Text } from 'cursor/canvas';

const baselineFullArtifact =
  'evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-05-02/sentence_routing_stage_b_discourse_pipeline_summary--sentence_routing_c2_session20_pc--gpt-5.4-mini--N5--20260502T024253Z.json';

const baselineEdgeArtifact =
  'evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-05-02/sentence_routing_stage_b_discourse_pipeline_summary--sentence_routing_c2_session20_pc_edge_slice_h1_h2_sentinel--gpt-5.4-mini--N5--20260502T024420Z.json';

const ablationFullArtifact =
  'evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-05-02/sentence_routing_stage_b_discourse_pipeline_summary--sentence_routing_c2_session20_pc--gpt-5.4-mini--N5--20260502T141720Z.json';

const ablationEdgeArtifact =
  'evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-05-02/sentence_routing_stage_b_discourse_pipeline_summary--sentence_routing_c2_session20_pc_edge_slice_h1_h2_sentinel--gpt-5.4-mini--N5--20260502T141757Z.json';

const stageBCandidatesDoc =
  'evals/sentence_routing_retrieval_falsification/STAGE_B_ENTITY_CANDIDATES.md';

const confidenceRows = [
  [
    'PC attachment',
    'Keep as current Stage B owner',
    'PC-only manifest routing is measurable and improving; full C2 still fails, but candidate ablation reduced distinct B2 failure units 21 to 15.',
    'Run on one unseen recap with existing PC hubs and require PC must-route recall plus low abstain leakage before broadening.',
  ],
  [
    'NPC hub creation / attachment',
    'Move to isolated pass',
    'Soft NPC candidates improved B1 content and missing-hub buckets, but did not remove ambient NPC to PC leakage.',
    'Build NPC timeline-first slice against existing C2 NPC hubs, then test Stafl/Marla/Stuart/Stacey hub gaps.',
  ],
  [
    'Location hub creation / attachment',
    'Sequence after NPC slice',
    'Location candidates are useful placeholders, but Location hubs have a broader schema and less consistent corpus coverage.',
    'Audit C2 location hub coverage and choose timeline-style updates before README state rewrites.',
  ],
];

const experimentRows = [
  ['Post-Caelynn full C2 baseline', '0/5', '21 distinct B2 failure units', '$0.255888', baselineFullArtifact],
  ['Entity-candidate ablation full C2', '0/5', '15 distinct B2 failure units', '$0.254735', ablationFullArtifact],
  ['Post-Caelynn H1/H2 edge baseline', '2/5', '1 distinct over-assigned abstain unit', '$0.035703', baselineEdgeArtifact],
  ['Entity-candidate ablation H1/H2 edge', '3/5', '2 distinct over-assigned abstain units', '$0.032244', ablationEdgeArtifact],
];

const bucketMovementRows = [
  ['B1 content distinct units', '2', '1', 'Improved', 'u-L0018-02 closed; u-L0026-06 remains a role-separation flake.'],
  ['B2 distinct failure units', '21', '15', 'Improved', 'Inventory hints help the model avoid some bogus PC ownership.'],
  ['b1_missing_expected_hub distinct units', '6', '2', 'Improved', 'Candidate placeholders reduce blank/missing PC routes.'],
  ['b1_over_route distinct units', '7', '3', 'Improved', 'Less accidental party/PC expansion in several cases.'],
  ['b2_over_assigned distinct units', '9', '10', 'Regressed', 'Remaining hard problem: ambient NPC/location beats still inherit PC hubs.'],
  ['H1/H2 edge pass rate', '2/5', '3/5', 'Improved', 'But edge failures are still abstain leakage, not missing candidate inventory.'],
];

const nextGateRows = [
  [
    '1',
    'Freeze Stage B PC contract',
    'Keep B1 as PC-thread classification plus placeholders, not a universal entity linker.',
    'One unseen PC-existing recap hits agreed PC recall / abstain thresholds without new prompt prose.',
  ],
  [
    '2',
    'NPC timeline-first slice',
    'Use Stage A events plus known NPC hubs; update NPC timeline rows before dossier-section writes.',
    'N=5 on one recap with existing NPC hubs shows stable slug attachment and no PC bleed-through.',
  ],
  [
    '3',
    'NPC hub-gap proving case',
    'Use Mossford NPCs as create/attach targets after the timeline shape is proven.',
    'Create-or-attach decisions are separable in artifacts: known hub vs missing hub proposal.',
  ],
  [
    '4',
    'Location coverage audit',
    'Do not test Location attachment until the corpus has enough compliant location hubs to grade.',
    'Lint/schema audit names candidate locations, missing hubs, and the first location-gold scenario.',
  ],
  [
    '5',
    'Cross-recap pilot',
    'Only after PC + NPC contracts are independently measured.',
    'Two different session recaps produce comparable per-entity artifacts and costs stay inside envelope.',
  ],
];

export default function StageBBucketMap() {
  return (
    <Stack gap={20}>
      <Stack gap={8}>
        <Row gap={8} wrap>
          <Pill tone="info" active>Entity Candidate Ablation</Pill>
          <Pill tone="warning" active>PC Pass Not Yet Green</Pill>
          <Pill tone="success" active>No Cost Regression</Pill>
        </Row>
        <H1>Stage B Hub Confidence Map</H1>
        <Text tone="secondary">
          Current decision surface after adding Stage 1-style NPC/location candidate hints to the split
          Stage B discourse pipeline. The question is no longer "add another B1 prompt rule?"; it is
          how much confidence we need in PC, NPC, and Location hub attachment before testing other recaps.
        </Text>
      </Stack>

      <Grid columns={4} gap={16}>
        <Stat value="0/5" label="Full C2 ablation pass rate" tone="warning" />
        <Stat value="3/5" label="H1/H2 edge ablation pass rate" tone="info" />
        <Stat value="21 -> 15" label="Full C2 B2 failure units" tone="success" />
        <Stat value="$0.254735" label="Full C2 ablation cost" />
      </Grid>

      <Callout tone="info" title="Ablation verdict">
        Explicit NPC/location candidates are useful as soft negative evidence and placeholder anchors. They
        improve B1 and shrink several B2 buckets, but they do not eliminate abstain leakage where an ambient
        NPC or location beat inherits a PC hub. Keep the candidate surface; stop broad B1 prompt tuning; move
        NPC and Location retrieval targets into isolated passes.
      </Callout>

      <H2>Ablation Snapshot</H2>
      <Table
        headers={['Cohort', 'Pass Rate', 'Key Failure Read', 'Cost Sum', 'Artifact']}
        rows={experimentRows}
        rowTone={['warning', 'info', 'info', 'success']}
        columnAlign={['left', 'right', 'left', 'right', 'left']}
      />

      <Text size="small" tone="secondary">
        Contract details and command: <Code>{stageBCandidatesDoc}</Code>.
      </Text>

      <Divider />

      <H2>What Moved</H2>
      <Table
        headers={['Metric', 'Baseline', 'Ablation', 'Read', 'Interpretation']}
        rows={bucketMovementRows}
        rowTone={['success', 'success', 'success', 'success', 'warning', 'info']}
        columnAlign={['left', 'right', 'right', 'left', 'left']}
      />

      <Divider />

      <H2>Confidence By Hub Type</H2>
      <Grid columns="1.1fr 1fr" gap={16}>
        <Stack gap={10}>
          <H3>What this means</H3>
          <Text>
            PC hub attachment is the closest to a usable contract because it already has manifest slugs,
            gold, reducer behavior, and costed cohorts. The remaining risk is not "does the system know PCs
            exist?" but "does it avoid assigning PCs to ambient NPC/location beats?"
          </Text>
          <Text>
            NPC and Location targets should not be smuggled into B1 as extra prompt prose. They need their
            own attachment passes so known-hub, missing-hub, and wrong-hub decisions can be graded separately.
          </Text>
        </Stack>

        <Card>
          <CardHeader>Decision</CardHeader>
          <CardBody>
            <Text>
              Treat Stage B as PC routing plus entity-candidate placeholders. The next architectural work is
              an NPC timeline-first attachment slice; Location follows after a hub-coverage audit.
            </Text>
          </CardBody>
        </Card>
      </Grid>

      <Table
        headers={['Surface', 'Recommended Role', 'Evidence', 'Next Confidence Gate']}
        rows={confidenceRows}
        rowTone={['info', 'success', 'warning']}
      />

      <Divider />

      <H2>Next Gates Before Other Recaps</H2>
      <Table
        headers={['Order', 'Gate', 'Purpose', 'Pass Condition']}
        rows={nextGateRows}
        rowTone={['info', 'success', 'success', 'warning', undefined]}
        columnAlign={['right', 'left', 'left', 'left']}
      />

      <Callout tone="warning" title="Do not broaden yet">
        Running many other recaps now would mostly measure mixed failure classes. First isolate PC routing,
        NPC attachment, and Location coverage so failures say which contract broke.
      </Callout>
    </Stack>
  );
}
