from __future__ import annotations

from evals.mirathorn_vertical_slice.run_council_room_question_set import (
    classify_answer,
    classify_answer_semantic,
    _semantic_token_present,
)


def test_localized_unchanged_trait_is_not_global_stale() -> None:
    answer = (
        "The chamber is disheveled and runes activated after the fight, "
        "but acoustics remain unchanged."
    )
    verdict, must_hits, stale_hits, global_stale_hits = classify_answer(
        must_tokens=["runes", "disheveled", "activated"],
        stale_tokens=["unchanged"],
        answer=answer,
        has_error=False,
    )
    assert "unchanged" in stale_hits
    assert not global_stale_hits
    assert verdict == "pass_updated"
    assert len(must_hits) >= 2


def test_global_stale_phrase_is_classified_as_stale() -> None:
    answer = "There are no observed or prep facts and nothing changed in the room."
    verdict, *_ = classify_answer(
        must_tokens=["runes", "disheveled", "activated"],
        stale_tokens=["unchanged"],
        answer=answer,
        has_error=False,
    )
    assert verdict == "fail_stale"


# --- Semantic equivalence tests ---


def test_semantic_killing_blow_matches_decapitated() -> None:
    assert _semantic_token_present("killing blow", "the wolf was decapitated")


def test_semantic_dead_matches_head_removed() -> None:
    assert _semantic_token_present("dead", "head removed from body")


def test_semantic_oily_sheen_fades_matches_partial() -> None:
    assert _semantic_token_present("oily sheen fades", "the oily sheen in his eyes fades")


def test_semantic_no_false_positive_on_unrelated() -> None:
    assert not _semantic_token_present("killing blow", "the wolf was alive and well")


def test_semantic_classify_promotes_wolf_status() -> None:
    """Answer says 'decapitated' (not literal 'killing blow'), semantic should pass."""
    answer = (
        "The Wolf is dead. Decapitated; head removed from body. "
        "The oily sheen in his eyes fades after death."
    )
    strict_v, strict_hits, *_ = classify_answer(
        must_tokens=["killing blow", "dead", "oily sheen fades"],
        stale_tokens=["alive"],
        answer=answer,
        has_error=False,
    )
    sem_v, sem_hits, *_ = classify_answer_semantic(
        must_tokens=["killing blow", "dead", "oily sheen fades"],
        stale_tokens=["alive"],
        answer=answer,
        has_error=False,
    )
    assert "killing blow" not in strict_hits
    assert "killing blow" in sem_hits
    assert sem_v == "pass_updated"


def test_semantic_does_not_weaken_stale_detection() -> None:
    answer = "Nothing changed in the council room."
    sem_v, *_ = classify_answer_semantic(
        must_tokens=["runes", "chandelier"],
        stale_tokens=["unchanged"],
        answer=answer,
        has_error=False,
    )
    assert sem_v == "fail_stale"


def test_semantic_dead_not_satisfied_by_vague_no_longer_active() -> None:
    assert not _semantic_token_present("dead", "the shop is no longer active this season")


def test_semantic_after_not_satisfied_by_generic_end_of_phrase() -> None:
    assert not _semantic_token_present("after", "at the end of the day the party rested")


def test_semantic_before_not_satisfied_by_lead_in_alone() -> None:
    assert not _semantic_token_present("before", "during the lead-in music")


def test_semantic_killing_blow_still_matches_real_death_paraphrase() -> None:
    """Guardrail: tightening broad tokens must not break real wolf-death paraphrases."""
    assert _semantic_token_present("killing blow", "he took a killing blow and fell")
