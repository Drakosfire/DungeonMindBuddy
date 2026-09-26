import { Badge, Button, Stack, Surface } from "./primitives";

export const Surfaces = () => (
  <Stack gap="large" style={{ maxWidth: "var(--ui-reading-width)" }}>
    <Surface tone="chrome" aria-label="Room chrome">
      Cheap room chrome keeps navigation and presence in the background.
    </Surface>
    <Surface tone="paper" aria-label="Current work">
      Warm paper gives the current table instrument the expensive visual weight.
    </Surface>
    <Surface tone="ops" aria-label="Prepared handout">
      Dark ops is a prepared handout, not a second recap.
    </Surface>
  </Stack>
);

export const Buttons = () => (
  <Stack direction="row" gap="medium" wrap>
    <Button>Quiet action</Button>
    <Button tone="action">Take action</Button>
    <Button tone="danger">Danger action</Button>
    <Button disabled>Unavailable action</Button>
  </Stack>
);

export const Badges = () => (
  <Stack direction="row" gap="small" wrap>
    <Badge>Reference</Badge>
    <Badge tone="current">Current</Badge>
    <Badge tone="danger">Attention</Badge>
  </Stack>
);

export const Stacks = () => (
  <Surface tone="chrome" aria-label="Stack spacing">
    <Stack gap="large">
      <Stack direction="row" wrap>
        <Badge>Recap</Badge>
        <Badge>World object</Badge>
        <Badge>Tool</Badge>
      </Stack>
      <Stack direction="row" gap="small" wrap>
        <Button>Inspect</Button>
        <Button tone="action">Open</Button>
      </Stack>
    </Stack>
  </Surface>
);
