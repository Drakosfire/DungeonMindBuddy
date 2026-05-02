import {
  BarChart,
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
} from "cursor/canvas";

const BUCKETS: Array<{
  code: string;
  name: string;
  desc: string;
  count: number;
  livePlayPct: number;
}> = [
  { code: "A", name: "Bookkeeping", desc: "travel hours, distances, table state", count: 33, livePlayPct: 22 },
  { code: "B", name: "Quick lookup", desc: "“what is 28”, “run it”, scalar Q", count: 58, livePlayPct: 18 },
  { code: "C", name: "Idea jot", desc: "creative seed, often parenthetical", count: 45, livePlayPct: 14 },
  { code: "D", name: "Generation", desc: "d20/d100, statblock, dossier, card", count: 200, livePlayPct: 12 },
  { code: "E", name: "Refinement", desc: "“try again”, “expand”, “make it tighter”", count: 50, livePlayPct: 28 },
  { code: "F", name: "Subagent", desc: "explicit “create a subagent…”", count: 15, livePlayPct: 7 },
  { code: "G", name: "Cross-link", desc: "link this to that, dossier hookup", count: 62, livePlayPct: 16 },
  { code: "H", name: "Meta", desc: "workflow, planning the planning", count: 75, livePlayPct: 5 },
];

const TIMELINE: Array<[string, string, string]> = [
  ["~1–1400", "Pre-play tooling", "Extraction Lab, corpus batch, subagent infra"],
  ["~1407–4663", "Vertical slices & product work", "Lysandra pipeline, planner benchmarks, recap ingest"],
  ["~4664", "PIVOT → upcoming-session prep", "“Welp we are out of time… plan for the upcoming session.”"],
  ["~4668", "Brainstorm-mode declared", "“Idea dump… no model assistance… flag as brainstorming.”"],
  ["~4748", "Travel bookkeeping layer", "“Keeping track of traveling… 6 and a half hours.”"],
  ["~4765", "Live-play behavior begins", "“Tell me what 28 on the traveling d100.”"],
  ["~4857–4888", "Peak live generation load", "Loot d100 → revisions → night-camp d100"],
  ["~4898", "Retrospective + brief for this canvas", "“We need a robust subagent deploy and report system.”"],
];

const LIVE_PLAY_TURNS: Array<{
  line: string;
  bucket: string;
  quote: string;
}> = [
  { line: "4664", bucket: "H", quote: "“Welp we are out of time… plan for the upcoming session.”" },
  { line: "4668", bucket: "C", quote: "“Brainstorming idea dump… no model assistance.”" },
  { line: "4673", bucket: "H", quote: "“Parallel doc tracking the steps… agentic loops.”" },
  { line: "4676", bucket: "D", quote: "“Quick prep… add Raucous_Saints to corpus.”" },
  { line: "4685", bucket: "C", quote: "“Document for story threads… collected and organized.”" },
  { line: "4690", bucket: "D", quote: "“Rumor, a scene… shop… chatty… Ephanna.”" },
  { line: "4697", bucket: "D", quote: "“Reflect… create intro for this session.”" },
  { line: "4702", bucket: "B", quote: "“1d100 table… traveling to the swamp… in the corpus.”" },
  { line: "4711", bucket: "D", quote: "“Construct a d100… north along the road.”" },
  { line: "4723", bucket: "D", quote: "“Invent… Sheriff… backstory… add to docs.”" },
  { line: "4737", bucket: "A", quote: "“Storm is coming from the north east.”" },
  { line: "4748", bucket: "A", quote: "“Keeping track of traveling… 6 and a half hours.”" },
  { line: "4758", bucket: "A", quote: "“Mossford 2 days… Mireward Reach 5 days.”" },
  { line: "4765", bucket: "B", quote: "“Tell me what 28 on the traveling d100.”" },
  { line: "4769", bucket: "C", quote: "“Double gold… conical hills… probably nothing.”" },
  { line: "4771", bucket: "D", quote: "“Dossier for Caelynn… call name ‘The Storm’.”" },
  { line: "4788", bucket: "F", quote: "“Create a subagent… Caelynn dossier and timeline.”" },
  { line: "4792", bucket: "D", quote: "“Dossier for Sara… fraternal twins.”" },
  { line: "4805", bucket: "D", quote: "“Thrinn needs a dossier… Branchborn.”" },
  { line: "4823", bucket: "D", quote: "“Make a d20 table… conical hills.”" },
  { line: "4831", bucket: "B", quote: "“What is 15.”" },
  { line: "4833", bucket: "E", quote: "“Expand on that.”" },
  { line: "4840", bucket: "B", quote: "“Scale… arcana check to learn.”" },
  { line: "4844", bucket: "D", quote: "“Robust description… statblock generator.”" },
  { line: "4853", bucket: "B", quote: "“What time of day are the drakes active?”" },
  { line: "4857", bucket: "D", quote: "“1d100 loot table for this drake nest.”" },
  { line: "4866", bucket: "E", quote: "“Try again, this kinda sucks and isn't rewards.”" },
  { line: "4875", bucket: "E", quote: "“90 to 100 should not be campaign pivots.”" },
  { line: "4879", bucket: "A", quote: "“Bonogo rolled 100… got 93 and 48… needs a card.”" },
  { line: "4888", bucket: "D", quote: "“d100 of night time… team is camping.”" },
  { line: "4898", bucket: "H", quote: "“Mine this and identify patterns.”" },
];

const REFINEMENT_LOOPS: Array<[string, string, string]> = [
  [
    "Geomantic drake nest loot d100",
    "≥2 user-driven rounds",
    "“Try again, this kinda sucks” → “90–100 should not be campaign pivots”",
  ],
  [
    "Mireward Reach road d100",
    "≥3 assistant edits",
    "Per-word bolding, 81–100 trim, formatting passes",
  ],
  [
    "Conical hill d20 entry 15",
    "≥2 expansion rounds",
    "“What is 15” → “Expand on that” → mechanical detail (DCs)",
  ],
];

const PAIN_POINTS: Array<{ tag: string; signal: string; cost: string }> = [
  {
    tag: "Long stream",
    signal: "Watching a d100 render token-by-token (loot, road, night camp)",
    cost: "Burns table energy; the GM context-switches before the ink dries",
  },
  {
    tag: "Refine cycle",
    signal: "“Try again, this kinda sucks” after a long generation",
    cost: "Two long generations for one usable artifact; doubled stall",
  },
  {
    tag: "Roll lookup as LLM",
    signal: "“What is 28” asked of the model instead of read-by-line from the file",
    cost: "Model-roundtrip for a deterministic file fetch",
  },
  {
    tag: "Side-thought hijack",
    signal: "Mirathorn aside dropped into the live thread (line 4898)",
    cost: "Either interrupts a roll or gets answered shallowly and lost",
  },
  {
    tag: "Inline dossier",
    signal: "Sara/Thrinn done synchronously while Caelynn used a subagent",
    cost: "Caelynn took ~1 turn off-thread; Sara/Thrinn ate live turns",
  },
];

const SUBAGENT_HISTORY: Array<[string, string, string]> = [
  ["Extraction Lab handoff", "/extraction-lab-operator", "Spec saved; user-guided creation pattern"],
  ["Stage & commit", "/stage-and-commit", "Stalled once; needed Await + transcript read"],
  ["Benchmark question curator", "Task + custom command", "Shipped 10 curated questions cleanly"],
  ["Caelynn dossier sweep", "Task (generalPurpose)", "Best in-thread example: full timeline + dossier returned"],
  ["This analysis", "Task (explore)", "Returned structured 9-section report → this canvas"],
];

const RECS: Array<{
  title: string;
  what: string;
  when: string;
}> = [
  {
    title: "Parking Lot",
    what: "One command (e.g. /park) appends a timestamped bullet to ParkingLot.md and returns immediately. Side thought captured, zero context spent.",
    when: "Any [C] or [H] message during live play. Mirathorn brain-itch goes here.",
  },
  {
    title: "Fire-and-forget table workers",
    what: "d20/d100 requests dispatch to a Task worker that writes the file and returns: file path, row count, banding summary, checksum. Main thread stays free.",
    when: "Default for any d20/d100/statblock/dossier > 30 lines.",
  },
  {
    title: "Two-phase table delivery",
    what: "Phase 1 (sync, <2s): bandings/headers/rules of the table. Phase 2 (async): worker fills the rows. The GM can keep talking while it writes.",
    when: "Live play d100s where the GM needs the *idea* now and the *content* in the next 30s.",
  },
  {
    title: "Roll lookup = grep, not LLM",
    what: "“What is 28 on X table” reads line 28 of the markdown file; no model call. Provide a /roll <table> <n> shortcut.",
    when: "Every die-result lookup at the table.",
  },
  {
    title: "Subagent report contract",
    what: "Every Task returns a fixed footer: artifact paths · open questions · blocking y/n · suggested next call. Drop into a single ReportInbox.md the user can scan between rolls.",
    when: "Standardize across all Task dispatches; required when run_in_background.",
  },
  {
    title: "Mode prefix or pill",
    what: "[BRAINSTORM] / [TABLE] / [BOOKKEEPING] / [LIVE] header on the first line of the user message tunes assistant behavior — short answers in LIVE, exploratory in BRAINSTORM.",
    when: "Whenever the GM consciously switches gears.",
  },
  {
    title: "Refinement budget",
    what: "After one “try again” on the same artifact, auto-offer to delegate the next pass to a subagent with the new constraint, instead of regenerating in the main thread.",
    when: "Triggered by [E] on the same artifact ≥1.",
  },
  {
    title: "Default-delegate parallel NPCs",
    what: "When the GM asks for 2+ dossiers in a row (Sara, Thrinn), auto-spawn parallel Task workers and aggregate. Caelynn proved this pattern works.",
    when: "≥2 dossier/statblock asks in a 5-turn window.",
  },
];

export default function LivePlayWorkflowAnalysis() {
  return (
    <Stack gap={24}>
      <Stack gap={6}>
        <H1>Live-play workflow analysis</H1>
        <Text tone="secondary">
          Mining the 4,898-line transcript from <Code>0792fca1</Code> for the patterns that
          appeared once active session prep started. Source: explore subagent report,
          line cites are JSONL line numbers.
        </Text>
      </Stack>

      <Grid columns={5} gap={16}>
        <Stat value="537" label="Total user turns" />
        <Stat value="31" label="Live-play turns (post-4664)" />
        <Stat value="3" label="Refinement loops (≥2 rounds)" />
        <Stat value="5" label="Subagent dispatches" tone="info" />
        <Stat value="4" label="d100 / d20 tables generated" />
      </Grid>

      <Divider />

      <Stack gap={8}>
        <H2>Where pre-planning ended and live play began</H2>
        <Text tone="secondary">
          The conversation lived in tooling for ~4,600 lines, then pivoted hard into
          session prep at <Code>~4664</Code>. From <Code>~4765</Code> onward the user's
          messages took on a recognizable at-the-table cadence: short imperatives, die-result
          lookups, past-tense roll narration, present-tense scene framing.
        </Text>
        <Table
          headers={["JSONL lines", "Phase", "Trigger / first signal"]}
          rows={TIMELINE.map(([lines, phase, sig]) => [lines, phase, sig])}
          rowTone={[undefined, undefined, "info", undefined, "info", "warning", "warning", undefined]}
          columnAlign={["left", "left", "left"]}
        />
      </Stack>

      <Divider />

      <Stack gap={8}>
        <H2>User-message taxonomy</H2>
        <Text tone="secondary">
          Eight buckets cover the full chat. Counts are sample-based estimates from the
          subagent's stratified read (head / mid / tail). The chart shows total volume;
          the table breaks out the live-play share.
        </Text>
        <BarChart
          height={220}
          categories={BUCKETS.map((b) => `${b.code} · ${b.name}`)}
          series={[{ name: "Total user turns", data: BUCKETS.map((b) => b.count) }]}
        />
        <Table
          headers={["Code", "Bucket", "What it is", "≈ count", "Share of live-play turns"]}
          rows={BUCKETS.map((b) => [
            <Pill key={b.code} active size="sm">
              {b.code}
            </Pill>,
            <Text key={b.name} weight="semibold">
              {b.name}
            </Text>,
            b.desc,
            String(b.count),
            `${b.livePlayPct}%`,
          ])}
          columnAlign={["left", "left", "left", "right", "right"]}
        />
      </Stack>

      <Divider />

      <Stack gap={8}>
        <H2>Live-play stretch — turn by turn</H2>
        <Text tone="secondary">
          Every user turn from the pivot at <Code>4664</Code> through this analysis request at
          <Code> 4898</Code>, in order. Bucket pill on the left, verbatim quote on the right.
        </Text>
        <Table
          headers={["Line", "Bucket", "Quote"]}
          rows={LIVE_PLAY_TURNS.map((t) => [
            <Code key={t.line}>{t.line}</Code>,
            <Pill key={`${t.line}-b`} size="sm" active>
              {t.bucket}
            </Pill>,
            <Text key={`${t.line}-q`} italic>
              {t.quote}
            </Text>,
          ])}
          columnAlign={["right", "center", "left"]}
          stickyHeader
          striped
          style={{ maxHeight: 420 }}
        />
      </Stack>

      <Divider />

      <Stack gap={12}>
        <H2>What hurt</H2>
        <Grid columns={2} gap={16}>
          {PAIN_POINTS.map((p) => (
            <Card key={p.tag}>
              <CardHeader trailing={<Pill size="sm" tone="warning" active>flow</Pill>}>
                {p.tag}
              </CardHeader>
              <CardBody>
                <Stack gap={6}>
                  <Text weight="semibold">{p.signal}</Text>
                  <Text tone="secondary">{p.cost}</Text>
                </Stack>
              </CardBody>
            </Card>
          ))}
        </Grid>
      </Stack>

      <Stack gap={8}>
        <H3>Refinement loops</H3>
        <Table
          headers={["Artifact", "Rounds", "What triggered each pass"]}
          rows={REFINEMENT_LOOPS}
          columnAlign={["left", "left", "left"]}
        />
      </Stack>

      <Divider />

      <Stack gap={8}>
        <H2>Subagent usage so far</H2>
        <Text tone="secondary">
          Subagents <Text weight="semibold">worked</Text> when used (Caelynn, benchmark
          curator, this analysis). The pattern just isn't yet the default — Sara and Thrinn
          ran on the main thread and ate live turns.
        </Text>
        <Table
          headers={["Task", "Mechanism", "Outcome"]}
          rows={SUBAGENT_HISTORY}
          columnAlign={["left", "left", "left"]}
        />
      </Stack>

      <Divider />

      <Stack gap={12}>
        <H2>Recommendations, ranked by table impact</H2>
        <Text tone="secondary">
          Each card is a discrete piece of plumbing. The first three are the highest-leverage
          for live play; the rest are cleanup that compounds.
        </Text>
        <Grid columns={2} gap={16}>
          {RECS.map((r, i) => (
            <Card key={r.title}>
              <CardHeader
                trailing={
                  <Pill size="sm" tone={i < 3 ? "success" : "info"} active>
                    {i < 3 ? "high" : "medium"}
                  </Pill>
                }
              >
                {`${i + 1}. ${r.title}`}
              </CardHeader>
              <CardBody>
                <Stack gap={8}>
                  <Text>{r.what}</Text>
                  <Row gap={8} align="center">
                    <Pill size="sm">when</Pill>
                    <Text size="small" tone="secondary">
                      {r.when}
                    </Text>
                  </Row>
                </Stack>
              </CardBody>
            </Card>
          ))}
        </Grid>
      </Stack>

      <Divider />

      <Stack gap={8}>
        <H2>Live-play vs brainstorm — text signals</H2>
        <Grid columns={2} gap={16}>
          <Card>
            <CardHeader trailing={<Pill size="sm" tone="warning" active>live</Pill>}>
              Live-play markers
            </CardHeader>
            <CardBody>
              <Stack gap={6}>
                <Text>Past-tense roll narration: <Text italic>“rolled a 100, got 93 and 48.”</Text></Text>
                <Text>Present-tense scene framing: <Text italic>“the team is camping on the sharp rise.”</Text></Text>
                <Text>Die-result lookups: <Text italic>“what is 28”, “what is 15.”</Text></Text>
                <Text>Short imperatives, urgency, no hedging.</Text>
                <Text>Bookkeeping deltas: hours, distances, who is where.</Text>
              </Stack>
            </CardBody>
          </Card>
          <Card>
            <CardHeader trailing={<Pill size="sm" tone="info" active>brainstorm</Pill>}>
              Brainstorm markers
            </CardHeader>
            <CardBody>
              <Stack gap={6}>
                <Text>Hypothetical framing: <Text italic>“what might be there.”</Text></Text>
                <Text>Permission-to-be-loose: <Text italic>“probably nothing.”</Text></Text>
                <Text>Long prose, world-building tone.</Text>
                <Text>Self-flagged mode: <Text italic>“flag as brainstorming.”</Text></Text>
                <Text>Future-tense, exploratory, multi-branch.</Text>
              </Stack>
            </CardBody>
          </Card>
        </Grid>
      </Stack>

      <Divider />

      <Stack gap={8}>
        <H2>Mirathorn parking-lot stub</H2>
        <Text tone="secondary">
          The trigger thought from line <Code>4898</Code> belongs in the parking lot the
          first recommendation builds. Stubbed here so it isn't lost while the plumbing
          gets built.
        </Text>
        <Card>
          <CardHeader trailing={<Pill size="sm" tone="info" active>open</Pill>}>
            Mirathorn — what is happening?
          </CardHeader>
          <CardBody>
            <Stack gap={6}>
              <Text weight="semibold">
                The GM needs very clear ideas about Mirathorn's state during the party's
                absence.
              </Text>
              <Text tone="secondary">
                Threads already in the corpus to mine: tainted jerky / supply chain (Session
                20), Sara's <Text italic>“who can I trust”</Text> wobble, Tealeaf line still
                hanging, Lysandra's reunion, Dustwalker decoy fallout, the curfew council,
                Stormbark Tea / Mossford handoff.
              </Text>
              <Text size="small" tone="tertiary">
                Drop into <Code>ParkingLot.md</Code> when the parking-lot mechanism exists.
              </Text>
            </Stack>
          </CardBody>
        </Card>
      </Stack>
    </Stack>
  );
}
