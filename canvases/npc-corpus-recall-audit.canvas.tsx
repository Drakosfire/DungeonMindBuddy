import {
  Callout,
  Code,
  Divider,
  Grid,
  H1,
  H2,
  Stack,
  Stat,
  Table,
  Text,
} from 'cursor/canvas';

const audit = {
  generatedAt: '2026-05-08T00:22:51Z',
  schema: 'dmb_npc_corpus_recall_audit_v2',
  reportPath: 'evals/npc_corpus_recall_audit/artifacts/last_npc_corpus_recall_audit.json',
  aggregate: {
    targetsTotal: 13,
    withAnyHub: 8,
    withLocationLink: 5,
    withWorldParentLink: 1,
    withDivergenceMode: 0,
    allOk: false,
    contractViolationCounts: {
      missing_hub: 5,
      campaign_hub_missing_world_parent_link: 3,
      missing_location_link: 3,
      campaign_hub_missing_divergence_mode: 4,
      missing_timeline: 4,
    },
  },
  rows: [
    { npc: 'grishna', tier: 'no_hub', score: 0, violations: ['missing_hub'] },
    { npc: 'glowkindle', tier: 'no_hub', score: 0, violations: ['missing_hub'] },
    {
      npc: 'pippa',
      tier: 'campaign_hub_no_world_link',
      score: 2,
      violations: [
        'campaign_hub_missing_world_parent_link',
        'missing_location_link',
        'campaign_hub_missing_divergence_mode',
      ],
    },
    {
      npc: 'bubbles_the_float_goat',
      tier: 'campaign_hub_no_world_link',
      score: 2,
      violations: [
        'campaign_hub_missing_world_parent_link',
        'missing_location_link',
        'campaign_hub_missing_divergence_mode',
      ],
    },
    { npc: 'kirfan', tier: 'no_hub', score: 0, violations: ['missing_hub'] },
    { npc: 'stuart', tier: 'hub_thin', score: 3, violations: ['missing_timeline'] },
    { npc: 'stacey_brambleback', tier: 'hub_thin', score: 3, violations: ['missing_timeline'] },
    { npc: 'marla_brambleback', tier: 'hub_thin', score: 3, violations: ['missing_timeline'] },
    { npc: 'sheriff_roderic_marr', tier: 'hub_thin', score: 3, violations: ['missing_timeline'] },
    { npc: 'mayor', tier: 'no_hub', score: 0, violations: ['missing_hub'] },
    {
      npc: 'captain_lysandra_ironveil',
      tier: 'linked_ready_baseline',
      score: 6,
      violations: ['campaign_hub_missing_divergence_mode'],
    },
    {
      npc: 'sara_mirathorn_operator',
      tier: 'campaign_hub_no_world_link',
      score: 2,
      violations: [
        'campaign_hub_missing_world_parent_link',
        'missing_location_link',
        'campaign_hub_missing_divergence_mode',
      ],
    },
    { npc: 'professor_tealeaf', tier: 'no_hub', score: 0, violations: ['missing_hub'] },
  ],
} as const;

export default function NpcCorpusRecallAuditCanvas() {
  const violationRows = Object.entries(audit.aggregate.contractViolationCounts).map(([k, v]) => [k, String(v)]);
  const npcRows = audit.rows.map((r) => [r.npc, r.tier, String(r.score), r.violations.join(', ') || '—']);
  const noHub = audit.rows.filter((r) => r.violations.includes('missing_hub')).map((r) => r.npc).join(', ');

  return (
    <Stack gap={18}>
      <H1>NPC corpus recall audit (world main vs campaign branch)</H1>
      <Text tone="secondary" size="small">
        Deterministic benchmark snapshot from <Code>{audit.reportPath}</Code> using schema{' '}
        <Code>{audit.schema}</Code>.
      </Text>

      {!audit.aggregate.allOk ? (
        <Callout tone="warning" title="Contract not satisfied">
          <Text>
            Branch contract currently fails. Most common issues: missing hubs, missing campaign world-parent links,
            and missing divergence metadata.
          </Text>
        </Callout>
      ) : (
        <Callout tone="success" title="Contract satisfied">
          <Text>All NPC rows meet world-parent, location-link, and divergence-mode requirements.</Text>
        </Callout>
      )}

      <Grid columns={5} gap={10}>
        <Stat value={String(audit.aggregate.targetsTotal)} label="Targets" />
        <Stat value={String(audit.aggregate.withAnyHub)} label="Any hub" />
        <Stat value={String(audit.aggregate.withLocationLink)} label="Location linked" />
        <Stat value={String(audit.aggregate.withWorldParentLink)} label="World parent linked" />
        <Stat value={String(audit.aggregate.withDivergenceMode)} label="Has divergence_mode" />
      </Grid>

      <Divider />
      <H2>Violation histogram</H2>
      <Table headers={['Violation', 'Count']} rows={violationRows} />

      <H2>Per-NPC contract rows</H2>
      <Table headers={['NPC', 'Tier', 'Score', 'Violations']} rows={npcRows} />

      <H2>Priority batch for hub creation</H2>
      <Text>
        NPCs with zero hub coverage in scope: <Code>{noHub || '—'}</Code>
      </Text>
      <Text tone="secondary" size="small">
        Generated from benchmark run timestamp: {audit.generatedAt}
      </Text>
    </Stack>
  );
}
