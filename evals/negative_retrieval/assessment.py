"""Assess independently observed turn evidence; absent proof is never a pass.

This assessor does not capture product behavior or judge semantic quality. Its
caller must supply independently reviewed judgments and complete journals.
"""

from .trace_observation import UNKNOWN


def assess(case, observation):
    """Score a case without treating missing observations as success."""
    for field in ("required_reads", "allowed_reads", "outcomes"):
        rows = case[field]
        if (not isinstance(rows, list) or any(not isinstance(row, str) or not row.strip() for row in rows)
                or len(rows) != len(set(rows))):
            raise ValueError(f"{field} must contain unique nonblank labels")
    catalog_budget = case["max_catalog_discoveries"]
    if type(catalog_budget) is not int or catalog_budget < 0:
        raise ValueError("max_catalog_discoveries must be a nonnegative integer")
    required = set(case["required_reads"])
    allowed = set(case["allowed_reads"])
    if UNKNOWN in allowed:
        raise ValueError("Unmapped acquisition cannot be an allowed source")
    if not required <= allowed:
        raise ValueError("Required reads must be allowed")
    if not case["outcomes"] or not set(case["outcomes"]) <= {"clarification", "proposal", "answer"}:
        raise ValueError("Unsupported outcome")
    reads = observation.get("reads")
    if reads is not None and (not isinstance(reads, list) or any(not isinstance(x, str) for x in reads)):
        raise ValueError("reads must be a list of source labels or null")
    complete = observation.get("journal_complete")
    if complete is not None and type(complete) is not bool:
        raise ValueError("journal_complete must be boolean or null")
    catalog_count = observation.get("catalog_discoveries")
    catalog_complete = observation.get("catalog_journal_complete")
    if catalog_count is not None and (type(catalog_count) is not int or catalog_count < 0):
        raise ValueError("catalog_discoveries must be a nonnegative integer or null")
    if catalog_complete is not None and type(catalog_complete) is not bool:
        raise ValueError("catalog_journal_complete must be boolean or null")
    # Incomplete journals can prove an unwanted read, but cannot prove absence.
    unknown_labels = reads is not None and UNKNOWN in reads
    unexpected = None if reads is None else sorted(set(reads) - allowed - {UNKNOWN})
    if unknown_labels and not allowed:
        unexpected.append(UNKNOWN)
    missing = (None if reads is None or complete is not True or unknown_labels
               else sorted(required - set(reads)))
    outcome = observation.get("outcome")
    checks = {
        "catalog_budget": (False if catalog_count is not None and catalog_count > catalog_budget
                           else True if catalog_count is not None and catalog_complete is True else None),
        "unexpected_retrieval": (False if unexpected else True if unexpected is not None and complete is True
                                 and not unknown_labels else None),
        "required_evidence": None if missing is None else not missing,
        "complete_journal": True if complete is True else None,
        "allowed_outcome": None if outcome is None else outcome in case["outcomes"],
        "completed_turn": observation.get("completed_turn"),
        "no_premature_mutation": observation.get("no_premature_mutation"),
        "semantic_quality": observation.get("semantic_quality"),
    }
    if required:
        checks["required_support"] = observation.get("required_support")
    if outcome == "clarification":
        for field in ("question_addresses_gap", "question_answerable", "question_not_already_answered",
                      "question_no_false_premises", "inline_questions", "no_retry_error",
                      "saved_and_reopened", "answer_sent", "answer_continued", "answer_reopened"):
            checks[field] = observation.get(field)
    if outcome == "proposal":
        checks["movable_proposal"] = observation.get("movable_proposal")
    for key, value in checks.items():
        if value is not None and type(value) is not bool:
            raise ValueError(f"{key} must be boolean or null")
    status = "fail" if False in checks.values() else "unproven" if None in checks.values() else "pass"
    return {"status": status, "checks": checks, "unexpected_reads": unexpected, "missing_reads": missing}


def summarize(cases, results):
    """Report bounds when incomplete observations cannot establish a rate.

    Cases with no allowed reads form the negative cohort. Required-read cases
    form the positive cohort. A known violation is counted even with an
    incomplete journal; absent required reads are unknown without one.
    """
    if set(cases) != set(results):
        raise ValueError("Each case must have exactly one assessment")

    def bounds(rows, key):
        if key == "negative_retrieval":
            values = []
            for case_id in rows:
                checks = results[case_id]["checks"]
                pair = (checks["unexpected_retrieval"], checks["catalog_budget"])
                values.append(False if False in pair else True if pair == (True, True) else None)
        else:
            values = [results[case_id]["checks"][key] for case_id in rows]
        failures = sum(value is False for value in values)
        unknown = sum(value is None for value in values)
        total = len(values)
        return {"cases": total, "failures": failures, "unknown": unknown,
                "minimum_rate": failures / total if total else None,
                "maximum_rate": (failures + unknown) / total if total else None}

    negative = [key for key, case in cases.items() if not case["allowed_reads"]]
    positive = [key for key, case in cases.items() if case["required_reads"]]
    return {"unnecessary_retrieval": bounds(negative, "negative_retrieval"),
            "missed_required_reads": bounds(positive, "required_evidence")}
