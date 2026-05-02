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

const fullArtifact =
  'evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-05-02/sentence_routing_stage_b_discourse_pipeline_summary--sentence_routing_c2_session20_pc--gpt-5.4-mini--N5--20260502T021400Z.json';

const edgeArtifact =
  'evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-05-02/sentence_routing_stage_b_discourse_pipeline_summary--sentence_routing_c2_session20_pc_edge_slice_h1_h2_sentinel--gpt-5.4-mini--N5--20260502T021433Z.json';

const previousFullArtifact =
  'evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-05-02/sentence_routing_stage_b_discourse_pipeline_summary--sentence_routing_c2_session20_pc--gpt-5.4-mini--N5--20260502T020904Z.json';

const previousEdgeArtifact =
  'evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-05-02/sentence_routing_stage_b_discourse_pipeline_summary--sentence_routing_c2_session20_pc_edge_slice_h1_h2_sentinel--gpt-5.4-mini--N5--20260502T020937Z.json';

const discoursePromptId = '692891a4ccd490ac97490e02';
const routingPromptId = '373c61d555956a0ccb659c19';

const unitSentences: Record<string, string> = {
  'u-L0014-03':
    'The first misses, but the second does enough damage to knock a group of insects out of the swarm.Then the swarm turns and envelopes Caelynn, the rest of the team can only see her dim shadow under all the flying insects.',
  'u-L0016-03':
    'Now that the swarm is around Caelynn, Karsemine is able to use her scimitar and short sword for a series of attacks, landing 4 hits on the swarm.',
  'u-L0016-07':
    'The team decides they have enough "testing" and should head back to tell the others what they discovered.',
  'u-L0016-06': 'As Thrin and Caelynn move back the swarm finally gives up and heads back into the forest.',
  'u-L0022-01':
    'As the group approaches the preparations happening in the field, they find Stafl singing and directing the workers from a makeshift throne of barrels on the back of a wagon.',
  'u-L0022-07': 'This, of course, only makes her more furious.',
  'u-L0024-01': 'She stands up to her full Bugbear height and begins to scream at him.',
  'u-L0024-03': 'Stafl takes a look around at the crowd to gauge their reactions.',
  'u-L0024-04': 'A farmer whispers to him that Stafl better step in and help because Marla is not someone to mess with.',
  'u-L0018-04': 'One of them is Stacey, the bugbear girl they are looking for.',
  'u-L0018-05':
    'She is in a heated argument with the other children who are accusing her of continuing to be too bossy.',
  'u-L0018-07':
    'Stacey immediately gets upset at seeing Stuart and tells him that he can’t play with them, but Stuart is undeterred.',
  'u-L0018-08':
    'He sticks his hand out and demands his gold back, convinced that she is the one that stole it.',
  'u-L0018-10':
    'Alarmed, she yells at Stuart and then throws her gold pouch at him before storming out the door.',
  'u-L0020-01':
    'Stuart is so happy with the outcome that he runs out the door, racing off to tell his mom the good news.',
  'u-L0020-08': 'Clearly shaken, Stacey runs home.',
  'u-L0024-05': 'They reveal that she is in charge of the workers in town and she means business.',
  'u-L0024-07':
    'Marla then grapples Bonogo and is about to do much worse when Caelynn comes to the rescue.',
  'u-L0024-09':
    'The rest of the Questionable Company decide to take a short rest as their final preparation.',
  'u-L0026-05': 'The mayor and sheriff congratulate the heroes and thank them again for all their help.',
  'u-L0026-06':
    'Marla approaches Caelynn and asks her how she should deal with Bonogo, but Ephanna quickly intervenes, letting her, and the town, know that the Questionable Company is leaving town to continue their journey.',
  'u-L0028-04':
    'She tells Caelynn that all she could hear was mumbling about the forest leaving and that something strange happened to the time.',
  'u-L0028-05':
    'Sara then connects Caelynn directly to Lysandra who is relieved and overjoyed that the group is ok and that they took care of the forest.',
  'u-L0028-07':
    'Lysandra tells her that she can’t remember much after the group left, only that she decided to go around the forest and she could smell meat while trying to sleep.',
  'u-L0028-08': 'She is exhausted and disoriented.',
  'u-L0030-01':
    'Using her extensive tracking skills, Karesmine is able to estimate the distance and direction that Lysandra may have traveled.',
  'u-L0032-03':
    'Stafl starts sorting through the provisions, convinced that someone snuck in the tainted meat before leaving Mirathorn.',
  'u-L0032-08': 'Sara is very concerned about who she can now trust in the city.',
  'u-L0030-03':
    'Thirty minutes later they come across an unusual sight: a wagon partly unloaded and horses wandering around a stack of crates.',
  'u-L0030-06': 'She says it is a tower where the voices are coming from and she knows where it is.',
  'u-L0030-11': 'Finally, after drinking the tea, Lysandra comes out of the spell.',
  'u-L0030-12': 'She is very confused, wondering where she is and how she got there.',
  'u-L0030-13': 'All that she is able to remember is voices in the dark after the group left into the forest.',
  'u-L0032-09': "She transfers Caelynn to Professor Tealeaf, but she doesn't pick up.",
  'u-L0034-01':
    'Caelynn continues to wait on the line for an answer from Tealeaf as the rest of the group set up a proper camp for a rest.',
  'u-L0034-03':
    'Ephanna plans to create a disguise and go back to town for new supplies, but for the moment the group is settling in for a rest around the camp.',
};

const targetRows = [
  [
    'u-L0034-01',
    'Rubric → caelynn',
    'Gold realign 2026-05-02',
    'Was whole-party vs stable model caelynn; scene-owner context added',
  ],
  [
    'u-L0032-09',
    'Rubric holds caelynn',
    'Scene-owner context 2026-05-02',
    'Flaky empties: same expected hub; harness nudge mirrors Bonogo pattern',
  ],
  ['u-L0018-04', '5/5 routed', 'Closed in latest cohort', 'Scene-owner context now held across all runs'],
  ['u-L0018-05', '5/5 routed', 'Closed in latest cohort', 'New context now held across all runs'],
  ['u-L0018-07', '5/5 routed', 'Closed', 'New context + prompt produced Bonogo every run'],
  ['u-L0018-08', '5/5 routed', 'Closed', 'Already had context; prompt now stable'],
  ['u-L0018-10', '5/5 routed', 'Closed', 'New full/edge context fixed B2 in both cohorts'],
  ['u-L0020-01', '5/5 routed', 'Closed in latest cohort', 'New context now held across all runs'],
  ['u-L0020-08', '5/5 routed', 'Closed in latest cohort', 'New context now held across all runs'],
];

const fullB1ContentRows = [
  ['u-L0026-06', 'discourse_mode', 'explicit_pc', 'scene_owner_pc', 'Run 3'],
  ['u-L0026-06', 'discourse_mode', 'explicit_pc', 'topic_pc', 'Run 4'],
];

const fullB2UnitRows = [
  ['u-L0016-06', 'must_route', 'Over-route', 'caelynn', 'caelynn + full roster', 'Run 2'],
  ['u-L0016-07', 'must_route', 'Missing expected hub', 'baergrom, bonogo, stafl', 'caelynn, ephanna, karsemine', 'Runs 1, 3'],
  ['u-L0022-01', 'must_route', 'Missing expected hub', 'baergrom, caelynn, ephanna, karsemine', 'stafl / bonogo, stafl', 'Runs 1, 2, 3'],
  ['u-L0022-07', 'must_route', 'Missing expected hub', 'bonogo', '[]', 'Run 0'],
  ['u-L0024-01', 'must_route', 'Missing expected hub', 'bonogo', '[]', 'Run 0'],
  ['u-L0024-03', 'must_route', 'Over-route', 'stafl', 'stafl, bonogo', 'Run 4'],
  ['u-L0024-04', 'must_route', 'Over-route', 'stafl', 'stafl, bonogo', 'Run 4'],
  ['u-L0024-05', 'must_abstain', 'Over-assigned', '[]', 'stafl, bonogo', 'Run 1'],
  ['u-L0024-09', 'must_route', 'Missing expected hub', 'baergrom, stafl', 'bonogo, caelynn, ephanna, karsemine', 'Run 3'],
  ['u-L0028-04', 'must_route', 'Missing expected hub', 'caelynn', '[]', 'Runs 0, 2'],
  ['u-L0028-05', 'must_route', 'Missing expected hub', 'caelynn', '[]', 'Run 0'],
  ['u-L0028-07', 'must_abstain', 'Over-assigned', '[]', 'caelynn', 'Runs 1, 3'],
  ['u-L0028-08', 'must_abstain', 'Over-assigned', '[]', 'caelynn', 'Runs 1, 3'],
  ['u-L0030-01', 'must_route', 'Over-route', 'karsemine', 'karsemine, caelynn', 'Run 3'],
  ['u-L0030-06', 'must_abstain', 'Over-assigned', '[]', 'caelynn', 'Runs 1, 3'],
  ['u-L0030-11', 'must_abstain', 'Over-assigned', '[]', 'caelynn', 'Runs 1, 3'],
  ['u-L0030-12', 'must_abstain', 'Over-assigned', '[]', 'caelynn', 'Runs 1, 3'],
  ['u-L0030-13', 'must_abstain', 'Over-assigned', '[]', 'caelynn', 'Runs 1, 3'],
  ['u-L0032-03', 'must_route', 'Over-route', 'stafl', 'stafl, karsemine', 'Run 3'],
  ['u-L0032-08', 'must_abstain', 'Over-assigned', '[]', 'caelynn', 'Run 1'],
  ['u-L0034-03', 'must_route', 'Missing expected hub', 'baergrom, bonogo, caelynn, karsemine, stafl', 'ephanna', 'Run 1'],
];

const edgeB1ContentRows: string[][] = [];

const edgeB2UnitRows = [
  ['u-L0028-07', 'must_abstain', 'Over-assigned', '[]', 'party-sized assignment', 'Runs 0, 1, 2'],
  ['u-L0030-06', 'must_abstain', 'Over-assigned / flag', '[]', 'caelynn or needs_new_hub_candidate', 'Runs 1, 2'],
];

export default function StageBBucketMap() {
  return (
    <Stack gap={20}>
      <Stack gap={8}>
        <Row gap={8} wrap>
          <Pill tone="warning" active>Failure Buckets</Pill>
          <Pill tone="success" active>Success Buckets</Pill>
          <Pill tone="info" active>Latest N=5 (2026-05-02 02:14Z)</Pill>
        </Row>
        <H1>Stage B Bucket Map</H1>
        <Text tone="secondary">
          B1 prompt now ties party-honor beats to <Code>routing_context.pc_party_names</Code> (ingested from{' '}
          <Code>_party_registry.json</Code>) plus explicit topic-vs-direct separation. Latest full C2 cohort:
          <Code>u-L0026-05</Code> is green; tradeoff is more abstain leakage and residual{' '}
          <Code>u-L0026-06</Code> discourse_mode flakes. Edge slice: 2/5 end-to-end; B2 is 45/5 pass/fail checks
          (abstain-only failures).
        </Text>
      </Stack>

      <Grid columns={4} gap={16}>
        <Stat value="315" label="Full C2 passing checks" tone="success" />
        <Stat value="55" label="Full C2 failing checks" tone="warning" />
        <Stat value="45" label="Edge passing checks" tone="success" />
        <Stat value="5" label="Edge failing checks" tone="warning" />
      </Grid>

      <Callout tone="info" title="Rubric note (post latest N=5 artifact)">
        <Code>u-L0034-01</Code> and <Code>u-L0032-09</Code> are judged Caelynn scenes: expected hubs stay{' '}
        <Code>caelynn</Code>; <Code>u-L0034-01</Code> moves off whole-party gold. Per-unit{' '}
        <Code>active_scene_owner_hubs=[&quot;caelynn&quot;]</Code> was added for both. Re-run the cohort to refresh
        bucket counts.
      </Callout>

      <Callout tone="success" title="Bonogo nudge result">
        The scoped scene-owner context worked for the target family: <Code>u-L0018-07</Code>, <Code>u-L0018-08</Code>,
        <Code>u-L0018-10</Code>, <Code>u-L0018-05</Code>, <Code>u-L0020-01</Code>, and <Code>u-L0020-08</Code>
        are all 5/5 in the new full C2 cohort. The earlier run-0 placeholder-only misses did not recur.
      </Callout>

      <H2>Target Row Outcomes</H2>
      <Table
        headers={['Unit ID', 'Sentence', 'Outcome', 'Residual Failure', 'Read']}
        rows={targetRows.map((row) => [row[0], unitSentences[row[0]], ...row.slice(1)])}
        rowTone={targetRows.map((row) => (row[2].startsWith('Closed') ? 'success' : 'warning'))}
      />

      <Divider />

      <H2>Failure Buckets</H2>
      <Table
        headers={['Cohort', 'Layer', 'Bucket', 'Failed Checks', 'Distinct Units', 'Total Failures', 'Flaky Units']}
        rows={[
          [
            'Full C2',
            'B2 gates',
            'b1_missing_expected_hub',
            '22',
            '9',
            '— (was u-L0034-01; rubric realigned)',
            'u-L0014-03, u-L0016-07, u-L0022-01, u-L0022-05, u-L0022-07, u-L0028-04, u-L0032-09, u-L0034-03',
          ],
          [
            'Full C2',
            'B2 gates',
            'b1_over_route',
            '8',
            '6',
            'none',
            'u-L0014-03, u-L0016-03, u-L0016-06, u-L0024-03, u-L0024-04, u-L0028-05',
          ],
          [
            'Full C2',
            'B2 gates',
            'b2_over_assigned',
            '25',
            '10',
            'none',
            'u-L0014-02, u-L0024-05, u-L0028-07, u-L0028-08, u-L0030-06, u-L0030-10, u-L0030-11, u-L0030-12, u-L0030-13, u-L0032-08',
          ],
          [
            'Full C2',
            'B1 content',
            'b1_content_*_mismatch',
            '2',
            '1',
            'none',
            'u-L0026-06',
          ],
          [
            'H1/H2 edge',
            'B2 gates',
            'b2_over_assigned',
            '5',
            '2',
            'none',
            'u-L0028-07, u-L0030-06',
          ],
        ]}
        rowTone={['danger', 'warning', 'warning', 'warning', 'warning']}
        columnAlign={['left', 'left', 'left', 'right', 'right', 'left', 'left']}
      />

      <Text size="small" tone="secondary">
        <Code>Total Failures</Code> means the unit failed in all five runs for that bucket. <Code>Flaky Units</Code>
        means at least one run passed and at least one run failed.
      </Text>

      <H2>Failure Buckets (Legacy Distinct View)</H2>
      <Table
        headers={['Cohort', 'Layer', 'Bucket', 'Distinct Units', 'Unit IDs']}
        rows={[
          [
            'Full C2',
            'B2 gates',
            'b1_missing_expected_hub',
            '9',
            'u-L0014-03, u-L0016-07, u-L0022-01, u-L0022-05, u-L0022-07, u-L0028-04, u-L0032-09, u-L0034-03',
          ],
          [
            'Full C2',
            'B2 gates',
            'b1_over_route',
            '6',
            'u-L0014-03, u-L0016-03, u-L0016-06, u-L0024-03, u-L0024-04, u-L0028-05',
          ],
          [
            'Full C2',
            'B2 gates',
            'b2_over_assigned',
            '10',
            'u-L0014-02, u-L0024-05, u-L0028-07, u-L0028-08, u-L0030-06, u-L0030-10, u-L0030-11, u-L0030-12, u-L0030-13, u-L0032-08',
          ],
          ['Full C2', 'B1 content', 'b1_content_*_mismatch', '1', 'u-L0026-06'],
          ['H1/H2 edge', 'B2 gates', 'b2_over_assigned', '2', 'u-L0028-07, u-L0030-06'],
        ]}
        rowTone={['danger', 'warning', 'warning', 'warning', 'warning']}
        columnAlign={['left', 'left', 'left', 'right', 'left']}
      />

      <H2>Every Failing Unit</H2>
      <Callout tone="info" title="How to read these rows">
        <Code>Expected</Code> is the gold route after expanding <Code>the_party</Code> to the session roster where
        applicable. <Code>Actual</Code> is what B1 plus the deterministic B2 reducer produced in failing runs.
      </Callout>

      <H3>Full C2: B1 Content Mismatch</H3>
      <Table
        headers={['Unit ID', 'Sentence', 'Field', 'Expected', 'Actual', 'Seen In']}
        rows={fullB1ContentRows.map((row) => [row[0], unitSentences[row[0]], ...row.slice(1)])}
        rowTone={fullB1ContentRows.map(() => 'warning' as const)}
      />

      <H3>Full C2: B2 Routing Gate Failures</H3>
      <Table
        headers={['Unit ID', 'Sentence', 'Gate', 'Failure', 'Expected', 'Actual', 'Seen In']}
        rows={fullB2UnitRows.map((row) => [row[0], unitSentences[row[0]], ...row.slice(1)])}
        rowTone={fullB2UnitRows.map((row) =>
          row[2] === 'Over-assigned' ? 'warning' : row[2] === 'Over-route' ? 'danger' : undefined
        )}
      />

      <H3>H1/H2 Edge: B1 Content Mismatch</H3>
      {edgeB1ContentRows.length > 0 ? (
        <Table
          headers={['Unit ID', 'Sentence', 'Field', 'Expected', 'Actual', 'Seen In']}
          rows={edgeB1ContentRows.map((row) => [row[0], unitSentences[row[0]], ...row.slice(1)])}
          rowTone={edgeB1ContentRows.map(() => 'warning' as const)}
        />
      ) : (
        <Text size="small" tone="secondary">
          None in this cohort (party-label + role-separation prompt held on the sentinel slice).
        </Text>
      )}

      <H3>H1/H2 Edge: B2 Routing Gate Failures</H3>
      <Table
        headers={['Unit ID', 'Sentence', 'Gate', 'Failure', 'Expected', 'Actual', 'Seen In']}
        rows={edgeB2UnitRows.map((row) => [row[0], unitSentences[row[0]], ...row.slice(1)])}
        rowTone={edgeB2UnitRows.map(() => 'warning' as const)}
      />

      <Divider />

      <H2>Success Buckets</H2>
      <Grid columns="1fr 1fr" gap={16}>
        <Card>
          <CardHeader trailing={<Pill tone="warning" size="sm">0/5 runs pass</Pill>}>Full C2 Session 20</CardHeader>
          <CardBody>
            <Stack gap={12}>
              <Grid columns={4} gap={12}>
                <Stat value="270" label="must_route pass" tone="success" />
                <Stat value="30" label="must_route fail" tone="warning" />
                <Stat value="45" label="must_abstain pass" tone="success" />
                <Stat value="25" label="must_abstain fail" tone="warning" />
              </Grid>
              <Text size="small" tone="secondary">
                Party-honor routing_context rule closed <Code>u-L0026-05</Code> in all five runs; missing-route pressure
                shifts back to phone-camp continuity (<Code>u-L0034-01</Code>) while abstain over-assignments ticked up.
              </Text>
              <Text size="small">
                Artifact: <Code>{fullArtifact}</Code>
              </Text>
            </Stack>
          </CardBody>
        </Card>

        <Card>
          <CardHeader trailing={<Pill tone="warning" size="sm">2/5 runs pass</Pill>}>H1/H2 Edge Slice</CardHeader>
          <CardBody>
            <Stack gap={12}>
              <Grid columns={4} gap={12}>
                <Stat value="30" label="must_route pass" tone="success" />
                <Stat value="0" label="must_route fail" tone="success" />
                <Stat value="15" label="must_abstain pass" tone="success" />
                <Stat value="5" label="must_abstain fail" tone="warning" />
              </Grid>
              <Text size="small" tone="secondary">
                Regressions are abstain-only: <Code>u-L0028-07</Code> and <Code>u-L0030-06</Code> picked up party-sized
                assignments in early runs when the model latched onto honor-language cues.
              </Text>
              <Text size="small">
                Artifact: <Code>{edgeArtifact}</Code>
              </Text>
            </Stack>
          </CardBody>
        </Card>
      </Grid>

      <Divider />

      <H2>Interpretation</H2>
      <Grid columns="1.1fr 1fr" gap={16}>
        <Stack gap={10}>
          <H3>What moved</H3>
          <Text>
            The Bonogo-context intervention now looks stable for the target family in this sample: the former
            <Code>u-L0018</Code>/<Code>u-L0020</Code> misses are gone across all five full C2 runs. That moves the
            residual risk away from the Bonogo scene-owner rule itself.
          </Text>
          <Text>
            The Karsemine realignment moves <Code>u-L0016-03</Code> out of the failure set: Caelynn is scene context,
            not the retrieval owner. The party-honor clause keyed off <Code>pc_party_names</Code> fixed{' '}
            <Code>u-L0026-05</Code> in this cohort; watch for honor-language bleeding into NPC-led abstain rows (
            <Code>u-L0028-07</Code>, <Code>u-L0030-06</Code> on the edge slice). <Code>u-L0026-06</Code> still needs
            stable explicit_pc vs stray scene_owner/topic modes.
          </Text>
        </Stack>

        <Card>
          <CardHeader>Next Focus</CardHeader>
          <CardBody>
            <Text>
              Shipped: party-honor beats use generic language tied to <Code>routing_context.pc_party_names</Code>, plus
              topic-vs-direct slug separation with explicit_pc when actors and topic-only PCs co-occur. Next: tighten
              guards so NPC-context abstain rows do not inherit party expansion; keep nudging <Code>u-L0026-06</Code>{' '}
              discourse_mode stability without undoing slug separation.
            </Text>
          </CardBody>
        </Card>
      </Grid>

      <Divider />

      <H2>Cost And Baseline</H2>
      <Table
        headers={['Cohort', 'Latest Cost', 'Previous Cost', 'Movement', 'Artifact']}
        rows={[
          ['Full C2', '$0.255552 sum / $0.051110 mean', '$0.255577 sum / $0.051115 mean', 'Flat prompt-tweak reroll; no regression', fullArtifact],
          ['H1/H2 edge', '$0.034961 sum / $0.006992 mean', '$0.032852 sum / $0.006570 mean', '+6.4% vs prior edge cohort; below 1.5× gate', edgeArtifact],
        ]}
      />
      <Text size="small" tone="secondary">
        Prior artifacts: <Code>{previousFullArtifact}</Code> and <Code>{previousEdgeArtifact}</Code>.
      </Text>
    </Stack>
  );
}
