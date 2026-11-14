# Regenerate the statblock Python models

From the Buddy repository root, run the pinned generator against the canonical
OpenAPI snapshot. The temporary output lets you verify parity before updating
the checked-in models.

```bash
integration=apps/live_control_server/integrations/dungeonmind_statblocks
scratch=$(mktemp -d)
uvx --python 3.14 --from datamodel-code-generator==0.35.0 datamodel-codegen \
  --input "$integration/openapi/dungeonbuddy-statblocks-v1.json" \
  --input-file-type openapi --output "$scratch/models.py" \
  --output-model-type pydantic_v2.BaseModel --target-python-version 3.13 \
  --use-annotated --use-union-operator --use-subclass-enum \
  --disable-timestamp --output-datetime-class AwareDatetime \
  --use-standard-collections --strict-nullable --enum-field-as-literal one \
  --collapse-root-models --extra-fields forbid

python3 - "$scratch/models.py" "$integration/generated/models.py" <<'PY'
import re
import sys
from pathlib import Path

generated = Path(sys.argv[1]).read_text().split("\n", 3)[3]
checked_in = Path(sys.argv[2]).read_text().split("\n", 6)[6]
generated = generated.replace("from enum import Enum", "from enum import StrEnum")
generated = generated.replace("(str, Enum):", "(StrEnum):")


def restore_discriminator(match):
    members = match[1].splitlines()
    members[-1] += ","
    indented = "\n".join("    " + line for line in members)
    return (
        "        list[\n            Annotated[\n"
        + indented
        + "\n                Field(discriminator='kind'),\n            ]\n        ]"
    )


generated, count = re.subn(
    r"        list\[\n(            DamageEffect(?:Input|Output)\n"
    r"(?:            \| \w+\n)*            \| HumanAdjudicatedEffect)\n        \]",
    restore_discriminator,
    generated,
)
if count != 14 or generated != checked_in:
    raise SystemExit("Generated models differ. Review the schema and generated model changes.")
print("Model body matches exactly.")
PY
```

The post-processing preserves the public string-enum behavior and the
`kind` discriminator on each nested effect union. When updating the
snapshot, review any change in the discriminator count and update the
source fingerprint headers to match the canonical file.
