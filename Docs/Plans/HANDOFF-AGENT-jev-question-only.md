# AGENT — question-only evidence acquisition experiment

ACTIVE under the operator's Jev/controller goal. PRIME solo; ARCHITECTURE independent
review. Serial successor to #1271 merged2604dca14e0a957b7ef3c2deada6c96e8d338d01.
Base that fetched Buddy main; branch codex/jev-question-only-acquisition;
non-serving /tmp/prime-recap-mention-boundaries. Open Ingest leases are disjoint.

Capability: optional experimental mode derives one requirement from the user question
and starts with no evidence or seed. Existing Jev legal-action judgments choose the
first retrieval action from reference-only discovery labels. Labels cannot satisfy
support. Host keeps unique actions, acquisition validation, conflict/unsupported
stopping and exact source scope. Preserve default/manual behavior for comparison.

Exclusive writes: this handoff; Docs/Plans/HANDOFF-AGENT-jev-controller-cohort.md;
evals/graph_memory_layer/jev_evidence_loop.py;
evals/graph_memory_layer/run_jev_controller_cohort.py;
tests/test_jev_evidence_loop.py; tests/test_jev_controller_cohort.py.
Private live comparison scripts/results stay outside Git. No new runtime/API contract,
dependency change or serving deployment. No Luna in this experiment; existing
GenerationEngine→TypeSafe Jev route only, no retries or uncertain replay. No World,
corpus, conversation or retained database writes.

Verification: unchanged default regression; first model input has only user question
and legal discovery hints, no evidence, manual requirements/seeds or gold; host rejects
unsupported sufficiency. Run frozen cohort with duplicate question variants collapsed,
then read-only Float/Council from exact saved source. Preserve failures and compare
source/gold coverage, stopping, actions, component latency, actual reported usage.
Independent semantic review before merge. Success is bounded question-only acquisition,
not arbitrary question accuracy or ordinary Agent adoption.

First frozen synthetic run: 4/5 expected outcomes. Same-time conflict falsely stopped
after source A without opening B. This experiment is not ready for ordinary adoption.
Preserve controller-question-only-01 and its false sufficient stop. Defer live
Float/Council calls until a separately reviewed competing-evidence policy addresses
this failure; no unchanged model replay. The failed case is now a development
regression, not an unseen validation case for its eventual repair.
