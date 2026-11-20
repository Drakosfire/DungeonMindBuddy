"""Provider-free source fidelity/accounting; none of these tests establish recall."""

from copy import deepcopy
import json
from hashlib import sha256
import pytest
from graph_memory.extraction.statement_source_catalog import (
    catalog,
    validate_catalog,
    CONTRACT,
)
from graph_memory.extraction.qualified_statement_proposals import parse


def output(source):
    return {
        "contract": CONTRACT,
        "catalog_sha256": source["catalog_sha256"],
        "mentions": [
            {
                "mention_id": "a",
                "label": "actor interpretation",
                "source_unit_ids": ["u1"],
            }
        ],
        "proposals": [
            {
                "proposal_id": "p1",
                "source_unit_ids": ["u1"],
                "context_unit_ids": [],
                "meaning": "a qualified claim",
                "mode": "uncertain",
                "reporter_mention": None,
                "referent_mentions": ["a"],
                "uncertainty": ["source-local ambiguity"],
                "qualifications": [
                    {"key": "observation", "value": "not onset or causality"}
                ],
                "episode": "e1",
                "unresolved": [],
            }
        ],
        "dispositions": [
            {
                "unit_id": u["unit_id"],
                "status": "proposed" if i == 0 else "skipped",
                "proposal_ids": ["p1"] if i == 0 else [],
                "reason": "model-declared processing",
            }
            for i, u in enumerate(source["units"])
        ],
        "limitations": ["not semantic completeness"],
    }


@pytest.mark.parametrize(
    "body",
    [
        "é\r\n\r\na Fey\n",
        " \t\r\nA\r\rB",
        "A\n\t \nB\n\n",
        "A",
        "A\u2028B\n\nC",
        "```\ncode\n\nmore code\n```\n\n|A|B|\n|1|2|\n\n- one\n- two\n",
        "same\n\nsame\n",
    ],
)
def test_complete_physical_partition_preserves_every_byte(body):
    value = catalog(body, {"source": "immutable"})
    assert validate_catalog(value) == body
    assert b"".join(u["text"].encode() for u in value["units"]) == body.encode()
    previous = 0
    for unit in value["units"]:
        assert unit["start_byte"] == previous
        raw = body.encode()[previous : unit["end_byte"]]
        assert raw.decode() == unit["text"]
        assert sha256(raw).hexdigest() == unit["sha256"]
        previous = unit["end_byte"]
    assert previous == len(body.encode())
    assert (
        catalog(body, {"source": "foreign"})["catalog_sha256"]
        != value["catalog_sha256"]
    )


def test_exact_line_terminators_and_leading_blanks():
    value = catalog("\r\n \t\rA\r\n\r\nB\n", {})
    assert [u["text"] for u in value["units"]] == ["\r\n \t\rA\r\n\r\n", "B\n"]
    assert len(catalog("A\u2028B", {})["units"]) == 1


@pytest.mark.parametrize("body", ["", " \t\n\r\n"])
def test_blank_source_refuses(body):
    with pytest.raises(ValueError):
        catalog(body, {})


def test_intervening_guard_sentence_is_host_materialized_not_model_copied():
    guard = "She will take 3-4 guards she trusts to meet us in the Warehouse District where she believes the tunnel comes up. "
    assert len(guard.encode()) == 113
    body = (
        "Concern about meat. "
        + guard
        + "An arcana check reveals another plane.\n\nA separate passage."
    )
    source = catalog(body, {})
    batch = output(source)
    batch["proposals"][0]["context_unit_ids"] = ["u2"]
    result = parse(json.dumps(batch), source)
    passages = result["passages"]["p1"]
    assert guard in passages["primary"][0]["text"]
    assert passages["context"][0]["text"] == "A separate passage."
    assert "quote" not in result["batch"]["proposals"][0]
    assert result["coverage"]["semantic_completeness"] == "not_established"
    assert result["embedded_content_factive"] is False


@pytest.mark.parametrize(
    "change",
    [
        "commitment",
        "handle",
        "duplicate",
        "missing_disposition",
        "duplicate_disposition",
        "unknown_disposition",
        "wrong_proposal",
        "false_proposed",
        "context_only",
        "copied_quote",
        "native_mention",
        "blank_reason",
    ],
)
def test_forgery_and_false_accounting_refuse(change):
    source = catalog("first\n\nsecond", {})
    batch = output(source)
    proposal = batch["proposals"][0]
    if change == "commitment":
        batch["catalog_sha256"] = "0" * 64
    elif change == "handle":
        proposal["source_unit_ids"] = ["foreign"]
    elif change == "duplicate":
        proposal["source_unit_ids"] = ["u1", "u1"]
    elif change == "missing_disposition":
        batch["dispositions"].pop()
    elif change == "duplicate_disposition":
        batch["dispositions"].append(batch["dispositions"][0])
    elif change == "unknown_disposition":
        batch["dispositions"][1]["unit_id"] = "foreign"
    elif change == "wrong_proposal":
        batch["dispositions"][0]["proposal_ids"] = ["unknown"]
    elif change == "false_proposed":
        batch["dispositions"][1]["status"] = "proposed"
    elif change == "context_only":
        proposal["context_unit_ids"] = ["u2"]
        batch["dispositions"][1].update(status="proposed", proposal_ids=["p1"])
    elif change == "copied_quote":
        proposal["quote"] = "first...second"
    elif change == "native_mention":
        batch["mentions"][0]["mention_id"] = "ent:canonical"
    elif change == "blank_reason":
        batch["dispositions"][1]["reason"] = " "
    with pytest.raises(ValueError):
        parse(json.dumps(batch), source)


@pytest.mark.parametrize(
    "field,value",
    [
        ("start_byte", 1),
        ("sha256", "0" * 64),
        ("unit_id", "forged"),
        ("text", "changed"),
    ],
)
def test_catalog_descriptor_tamper_refuses(field, value):
    source = deepcopy(catalog("é\n\nB", {}))
    source["units"][0][field] = value
    with pytest.raises(ValueError):
        parse(json.dumps(output(source)), source)


def test_context_and_mentions_do_not_certify_actor_episode_recall():
    source = catalog("Torbin shows oily eyes. Bill has different symptoms.\n", {})
    batch = output(source)
    batch["proposals"][0]["meaning"] = "Bill has symptoms"
    result = parse(json.dumps(batch), source)
    assert "Torbin" in result["passages"]["p1"]["primary"][0]["text"]
    assert "Torbin" not in result["batch"]["proposals"][0]["meaning"]
    assert result["coverage"]["semantic_completeness"] == "not_established"
    # Structurally complete processing can contain no extracted claims at all.
    batch.update(mentions=[], proposals=[])
    batch["dispositions"][0].update(status="unresolved", proposal_ids=[])
    assert parse(json.dumps(batch), source)["batch"]["proposals"] == []
