"""One atomic WK object and discovery/attribution links; no direct event facts."""

from worldkeeper.application import contracts as wk
from graph_memory.vnext.domain_runtime import CAMPAIGN_SCOPE_AXIS, GM_LABEL
from .registry_standing_consumer import canonical, digest

SCHEMA = "dmb_source_statement_v1"
ABOUT = "dungeonbuddy.custom:about"
REPORTED_BY = "dungeonbuddy.custom:reported_by"
PRODUCER = "dungeonbuddy:source-statement-v1"


def publication_id(clause):
    return "dmb-statement:v1:" + digest(clause)


def intent(space_id, payload, evidence_ref_id):
    metadata = wk.AssertionMetadata(
        scope=(wk.ScopeBinding(CAMPAIGN_SCOPE_AXIS, payload["clause"]["campaign"]),),
        visibility=wk.Visibility("labels_any", (GM_LABEL,)),
        epistemic_basis="asserted",
        claim_mode="dungeonbuddy.claim:fact",
        standing="established",
        evidence_ref_ids=(evidence_ref_id,),
        temporal_scope=wk.TemporalScope(kind="unknown"),
    )
    operations = [
        wk.CreateObject(
            "statement",
            (
                wk.CreateFact(
                    "qualified-payload",
                    "dnd5e:summary",
                    wk.LiteralFactValue(canonical(payload).decode()),
                    metadata,
                ),
            ),
        )
    ]
    for index, target in enumerate(payload["referents"]):
        operations.append(
            wk.CreateRelationship(
                "about:" + str(index),
                wk.ResultOf("statement"),
                ABOUT,
                wk.DurableObjectRef(target),
                metadata,
            )
        )
    if payload["reporter"]:
        operations.append(
            wk.CreateRelationship(
                "reporter",
                wk.ResultOf("statement"),
                REPORTED_BY,
                wk.DurableObjectRef(payload["reporter"]),
                metadata,
            )
        )
    return wk.WorldChangeIntent(space_id, PRODUCER, tuple(operations))
