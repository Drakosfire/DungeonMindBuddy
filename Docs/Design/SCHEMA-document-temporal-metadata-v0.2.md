# Schema: Document Temporal Metadata v0.2 (Forward-only)

**Repo:** `DungeonMindBuddy`  
**Status:** Draft contract (forward-only; no backwards-compat requirements)  

## Goals

- Replace ambiguous `session: null` semantics with explicit temporal intent.
- Support reference documents that are:
  - session-specific (recaps/prep)
  - campaign-stateful (living notes / ledgers / dossiers)
  - evergreen (timeless/static reference artifacts)
- Provide universal lineage fields:
  - `origin_session`
  - `last_updated_session`

## Frontmatter fields (campaign-layer documents)

These fields live in markdown YAML frontmatter and compile into `DocumentMetadata`.

- **`temporal_scope`**: `session_specific | campaign_stateful | evergreen`
- **`session`**: integer session number (only meaningful for `session_specific`)
- **`origin_session`**: earliest session this doc’s subject matter enters campaign canon (optional)
- **`last_updated_session`**: latest session after which doc was materially updated (optional)

### Canonical interpretation

- **`session_specific`**
  - One-session document (e.g., recap, prep).
  - `session` **required**.
  - `origin_session` should usually equal `session`.
  - `last_updated_session` may equal `session` or be later if revised.

- **`campaign_stateful`**
  - Not a single session, but evolves over campaign time (living notes/ledgers).
  - `session` must be `null`.
  - `origin_session` optional but recommended.
  - `last_updated_session` optional but recommended.

- **`evergreen`**
  - Timeless/static reference artifact (items, templates/layout docs, stable lore).
  - `session` must be `null`.
  - `origin_session` optional (useful if introduced during play).
  - `last_updated_session` optional (useful if the artifact is maintained).

## Required invariants

### Global

- If `canon_layer=world`:
  - `campaign_id=null`
  - `temporal_scope=evergreen`
  - `session=null`
  - `origin_session=null`
  - `last_updated_session=null`

- If `canon_layer=campaign`:
  - `campaign_id` required
  - `temporal_scope` required

### Temporal rules

- If `temporal_scope=session_specific`:
  - `session` required and \( \ge 1 \)
- If `temporal_scope in {campaign_stateful, evergreen}`:
  - `session` must be `null`
- If both are present:
  - `last_updated_session >= origin_session`
- If `session` and `last_updated_session` are present:
  - `last_updated_session >= session`

## Recommended policy by `document_class`

- **`play`**:
  - `temporal_scope=session_specific`
  - `session` required
- **`planning`**:
  - usually `temporal_scope=session_specific` with `session` required
  - allow `campaign_stateful` for long-lived planning docs
- **`reference`**:
  - choose between:
    - `campaign_stateful` for living notes/ledgers/dossiers
    - `evergreen` for items/templates/static artifacts
- **`world`**:
  - `temporal_scope=evergreen`

## JSON Schema (document_metadata.schema.json)

This is the intended `document_metadata.schema.json` shape (v0.2).

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "document_metadata.schema.json",
  "title": "DungeonBuddy Document Metadata v0.2",
  "type": "object",
  "required": ["title", "document_class", "canon_layer", "source_class", "temporal_scope"],
  "properties": {
    "title": { "$ref": "common.schema.json#/$defs/nonEmptyString" },
    "document_class": { "type": "string", "enum": ["world", "play", "planning", "reference"] },
    "canon_layer": { "$ref": "common.schema.json#/$defs/canonLayer" },
    "campaign_id": { "$ref": "common.schema.json#/$defs/nullableId" },
    "source_class": { "$ref": "common.schema.json#/$defs/sourceClass" },

    "temporal_scope": {
      "type": "string",
      "enum": ["session_specific", "campaign_stateful", "evergreen"]
    },
    "session": { "$ref": "common.schema.json#/$defs/sessionIntOrNull" },
    "origin_session": { "$ref": "common.schema.json#/$defs/sessionIntOrNull" },
    "last_updated_session": { "$ref": "common.schema.json#/$defs/sessionIntOrNull" }
  },
  "allOf": [
    {
      "if": { "properties": { "canon_layer": { "const": "world" } } },
      "then": {
        "properties": {
          "campaign_id": { "type": "null" },
          "temporal_scope": { "const": "evergreen" },
          "session": { "type": "null" },
          "origin_session": { "type": "null" },
          "last_updated_session": { "type": "null" },
          "source_class": { "const": "seed_reference" }
        }
      }
    },
    {
      "if": { "properties": { "canon_layer": { "const": "campaign" } } },
      "then": {
        "required": ["campaign_id"],
        "properties": {
          "campaign_id": {
            "type": "string",
            "minLength": 1,
            "pattern": "^[A-Za-z0-9_.:-]+$"
          }
        }
      }
    },
    {
      "if": { "properties": { "temporal_scope": { "const": "session_specific" } } },
      "then": {
        "required": ["session"],
        "properties": { "session": { "type": "integer", "minimum": 1 } }
      }
    },
    {
      "if": { "properties": { "temporal_scope": { "enum": ["campaign_stateful", "evergreen"] } } },
      "then": { "properties": { "session": { "type": "null" } } }
    }
  ],
  "unevaluatedProperties": false
}
```

## Examples

### Session recap (`session_specific`)

```yaml
---
title: "Session 12 - One Persistent Bugbear"
document_class: play
canon_layer: campaign
campaign_id: longmont-c1
source_class: observed_session_recap
temporal_scope: session_specific
session: 12
origin_session: 12
last_updated_session: 12
---
```

### Living campaign notes (`campaign_stateful`)

```yaml
---
title: "Campaign 2 Notes"
document_class: reference
canon_layer: campaign
campaign_id: longmont-c2
source_class: ledger_or_dossier
temporal_scope: campaign_stateful
session: null
origin_session: 1
last_updated_session: 19
---
```

### Evergreen item reference (`evergreen`)

```yaml
---
title: "Item: The Slinkstone"
document_class: reference
canon_layer: campaign
campaign_id: longmont-c2
source_class: ledger_or_dossier
temporal_scope: evergreen
session: null
origin_session: 7
last_updated_session: null
---
```

### Template/layout doc (`evergreen`, no lineage)

```yaml
---
title: "Card Front Layout"
document_class: reference
canon_layer: campaign
campaign_id: longmont-c2
source_class: other
temporal_scope: evergreen
session: null
origin_session: null
last_updated_session: null
---
```
