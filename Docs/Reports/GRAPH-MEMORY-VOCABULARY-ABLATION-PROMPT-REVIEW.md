# Graph Memory Vocabulary Ablation — Prompt Review

Generated: 2026-06-30T20:19:17Z

This report shows the corpus/registry-derived vocabulary packet and the exact compact vocabulary context rendered into node and edge extraction prompts. It is a manual-review artifact; it does not contain LLM output.

## Bed: `c1s1-stonebridge`

- Campaign/session: `longmont-c1` / `session-1`
- Packet: `packet:vocab:8a7c6a045ddb`
- Known names: 12
- Type hints: 11
- Predicate hint subjects: 7
- Do-not-merge hints: 2
- Containment hints: 1

### Known names and type hints

- `Bonogo` — `actor`
- `Captain Lysandra Ironveil` — `actor`
- `Glowkindle` — `actor`
- `Grishna` — `actor`
- `Karsemine` — `actor`
- `Mireward Reach` — `place`
- `Stone Bridge` — `place`
- `The River's Edge Pub` — `place`
- `The Shepherd` — `actor`
- `Torbin Jove` — `actor`
- `Wizard's Tower Brewing Co` — `place`
- `stone bridge` — `unknown`

### Predicate hints

- `Bonogo`: `present_at`
- `Glowkindle`: `present_at`, `located_in`
- `Grishna`: `present_at`
- `Karsemine`: `present_at`
- `Stone Bridge`: `located_in`, `present_at`
- `The River's Edge Pub`: `located_in`
- `Wizard's Tower Brewing Co`: `located_in`, `present_at`

### Do-not-merge hints

- `vocab:c1s1:stone-bridge` != `vocab:c1s1:stone-bridge-landmark` — Stone Bridge town vs literal stone bridge landmark must remain visible.
- `vocab:c1s1:wizards-tower-brewing-co` != `vocab:c1s1:wizards-tower-org` — Place vs organization ambiguity for Wizard's Tower Brewing Co.

### Containment hints

- `The River's Edge Pub` -> `Stone Bridge`

### Node prompt contexts

#### `actor_pass`

```text
Vocabulary context for node extraction — actor_pass:

Known scoped names for this pass:
- Bonogo [actor]
- Captain Lysandra Ironveil [actor]
- Glowkindle [actor]
- Grishna [actor]
- Karsemine [actor]
- The Shepherd [actor]
- Torbin Jove [actor]

Predicate hints for later edge extraction:
- Bonogo: present_at
- Glowkindle: located_in, present_at
- Grishna: present_at
- Karsemine: present_at

Do-not-merge cautions:
- vocab:c1s1:stone-bridge != vocab:c1s1:stone-bridge-landmark
- vocab:c1s1:wizards-tower-brewing-co != vocab:c1s1:wizards-tower-org
```

#### `location_pass`

```text
Vocabulary context for node extraction — location_pass:

Known scoped names for this pass:
- Mireward Reach [place]
- Stone Bridge [place]
- The River's Edge Pub [place]
- Wizard's Tower Brewing Co [place]

Predicate hints for later edge extraction:
- Stone Bridge: located_in, present_at
- The River's Edge Pub: located_in
- Wizard's Tower Brewing Co: located_in, present_at

Do-not-merge cautions:
- vocab:c1s1:stone-bridge != vocab:c1s1:stone-bridge-landmark
- vocab:c1s1:wizards-tower-brewing-co != vocab:c1s1:wizards-tower-org

Containment hints:
- The River's Edge Pub -> Stone Bridge
```

#### `collective_pass`

(No vocabulary context rendered for this pass.)

#### `object_pass`

(No vocabulary context rendered for this pass.)

#### `thread_pass`

(No vocabulary context rendered for this pass.)

### Edge prompt context

```text
Vocabulary context for edge extraction:

Known names:
- Bonogo [actor]
- Captain Lysandra Ironveil [actor]
- Glowkindle [actor]
- Grishna [actor]
- Karsemine [actor]
- Mireward Reach [place]
- Stone Bridge [place]
- stone bridge
- The River's Edge Pub [place]
- The Shepherd [actor]
- Torbin Jove [actor]
- Wizard's Tower Brewing Co [place]

Predicate hints:
- Bonogo: present_at
- Glowkindle: located_in, present_at
- Grishna: present_at
- Karsemine: present_at
- Stone Bridge: located_in, present_at
- The River's Edge Pub: located_in
- Wizard's Tower Brewing Co: located_in, present_at

Do-not-merge cautions:
- vocab:c1s1:stone-bridge != vocab:c1s1:stone-bridge-landmark
- vocab:c1s1:wizards-tower-brewing-co != vocab:c1s1:wizards-tower-org

Containment hints:
- The River's Edge Pub -> Stone Bridge
```

