# Regenerate the statblock Python models

Use an installed Python 3.14 and uv. This pins the generator to 0.46.0, which
preserves required nullable fields. The canonical OpenAPI requires explicit
`ruleset`, `movement` and `proficiency_bonus` values even when those values are
null. Preserve that distinction from omitted fields.

From the Buddy repository root, run the complete recipe below. The lab wrapper
checks Projects storage and contains tool caches and scratch there. No Python
download is permitted. It compares the complete normalized body without editing
the checked-in models; temporary model output is removed on exit.

```bash
task_slug="statblock-models-$(date +%s)-$$"
UV_PYTHON_DOWNLOADS=never scripts/run_local_lab.sh "$task_slug" bash <<'SH'
set -euo pipefail
integration=apps/live_control_server/integrations/dungeonmind_statblocks
scratch=$(mktemp -d "$TMPDIR/models.XXXXXX")
trap 'rm -rf -- "$scratch"' EXIT
uvx --python 3.14 --from datamodel-code-generator==0.46.0 datamodel-codegen \
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

# Preserve Buddy's scalar interface, rather than exposing a RootModel wrapper.
# Exact shape/count guards refuse a changed constraint or generator structure.
proficiency_root = """class ProficiencyBonus(RootModel[int]):
    root: Annotated[
        int,
        Field(
            description='Must match rating on the standard 5e challenge-rating table.',
            ge=0,
            title='Proficiency Bonus',
        ),
    ]


"""
if generated.count(proficiency_root) != 1:
    raise SystemExit("Unexpected proficiency root model; review the schema and generator.")
generated = generated.replace(proficiency_root, "")
if generated.count("ProficiencyBonus | None") != 1:
    raise SystemExit("Unexpected proficiency reference; review the generated interface.")
generated = generated.replace("ProficiencyBonus | None", "Annotated[int, Field(ge=0)] | None")


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
SH
```

Post-processing preserves public string enums, fourteen nested effect-union
discriminators, and the constrained integer proficiency interface. Shape/count
guards and full-body comparison fail when generator/schema changes need review.
The model header fingerprint and exported `generated.OPENAPI_FINGERPRINT` must
match the canonical snapshot. Generated descriptions follow that snapshot.

When updating the schema, review the raw generated output and the complete model
diff before deliberately updating the checked-in body and fingerprint headers.
Recheck required/null/omitted behavior, scalar values, JSON round trips and
captured DTO compatibility. Do not relax comparison guards merely to get a pass.
Historical captures retain their capture-time identities; see their
[provenance guide](../../../../tests/fixtures/statblocks/v1/server_transcripts/README.md).
