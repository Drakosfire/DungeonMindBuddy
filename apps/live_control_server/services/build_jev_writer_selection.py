"""Final parent-owned controller phase; exact APP proof precedes one writer."""
from __future__ import annotations

import hashlib
from uuid import uuid4

from application_state.agent_conversation import types as ledger
from application_state.agent_conversation import writer_evidence_selection as selection
from .build_jev_accounting import DecisionCapacityError
from .build_jev_dispatch import continuation_binding, prepared_driver_view
from .build_jev_driver import DriverDecisionProjection
from .build_jev_transitions import DecisionIntent, DecisionQuestion


class WriterSelectionDriver:
    def __init__(self, adapter, acquisition_driver, terminal):
        if not isinstance(adapter._broker_execution().policy, ledger.BuildSelectedSourceActionControllerWriterPolicyV1):
            raise ValueError("Writer selection requires its frozen policy")
        if adapter.context_capture is None or terminal.get("status") == "refused":
            raise ValueError("Writer selection requires admissible retrieval and protected capture")
        self.adapter, self.acquisition_driver, self.terminal = adapter, acquisition_driver, terminal
        self._used = False
        self._prepared = None
        self.receipt = None
        self._material = self._optional_material()
        self.catalog = self._catalog()
        _, sources, sections = self._material
        if (set(sources) != {eid for unit in self.catalog.values() for eid in unit.get("source_event_ids", [])}
            or set(sections) != {unit["section"]["read_id"] for unit in self.catalog.values()
                                 if unit["kind"] == "saved_section"}):
            raise ValueError("Writer selection catalog differs from complete acquired material")
        self.state = selection.selection_state(adapter.turn, self.catalog, terminal, continuation_binding(adapter))
        self._questions = selection.questions(self.catalog)
        self.step = DecisionIntent(request_id="writer-selection:" + selection.digest(self.state),
            phase="writer_selection", state={"writer_selection_policy": selection.POLICY},
            questions=tuple(DecisionQuestion(name=name, kind="choice", question=q["instructions"],
                                             options=selection.JUDGMENTS)
                            for name, q in self._questions.items()))
        self._plan = None

    def _optional_material(self):
        from application_state.agent_conversation.authored_graph_references import source_event_ids
        graph, sources, sections = self.acquisition_driver._material()
        mandatory = {str(eid) for eid in source_event_ids(self.adapter._broker_execution())}
        return graph, tuple(sorted(set(sources) - mandatory)), sections

    def _catalog(self):
        if self._optional_material() != self._material:
            raise ValueError("Acquired material changed during writer selection")
        return selection.acquired_catalog(self.adapter._broker_execution(),
            self.adapter.context_capture.trace.model_dump(mode="json", by_alias=True))

    def stage(self):
        a = self.adapter
        if self._used or self._plan is not None or not self.catalog or self._catalog() != self.catalog:
            raise ValueError("No fresh exact writer-selection request")
        _, sources, sections = self._material
        self._plan = DriverDecisionProjection(selection.canonical(self.state), selection.canonical(self._questions),
            self.step.request_id, len(a._broker_execution().events), str(a.last_provider_attempt_id),
            (), sources, sections)
        return self._plan

    def authorize(self, prepared):
        a, plan = self.adapter, self._plan
        if (self._used or plan is None or a.failure is not None or self._catalog() != self.catalog
            or plan.event_sequence != len(a._broker_execution().events)
            or plan.prior_provider_attempt_id != str(a.last_provider_attempt_id)):
            return False
        try:
            view = prepared_driver_view(prepared, plan, accounting=getattr(a, "_build_jev_accounting", None))
        except DecisionCapacityError as exc:
            self.admission_failure = exc
            return False
        except (ValueError, KeyError, TypeError, AttributeError):
            return False
        a._prepared_build_authorizing = view
        a._active_build_jev_expected_state = plan.state()
        a._active_build_driver_projection = plan
        try:
            accepted = a.authorize(view)
        finally:
            a._prepared_build_authorizing = None
            a._active_build_jev_expected_state = None
            a._active_build_driver_projection = None
        if accepted:
            self._used, self._prepared = True, prepared
            a._prepared_build_decision = prepared
        return accepted

    def accept_response(self, result):
        a = self.adapter
        if (not self._used or self._prepared is None or self.receipt is not None
            or self._prepared.attempt_id != str(a.last_provider_attempt_id)
            or self._catalog() != self.catalog):
            raise ValueError("No unique acknowledged writer-selection response")
        response = result.model_dump(mode="json")
        response_json = selection.canonical(response)
        a.context_capture.controller_decision_response(response_json,
            producing_provider_attempt_id=a.last_provider_attempt_id)
        judgments = selection.response_judgments(self.catalog, response)
        return self._settle(judgments, response_json)

    def settle_empty(self):
        if self.catalog or self._used or self.receipt is not None:
            raise ValueError("Only an empty acquired catalog can settle deterministically")
        return self._settle({}, None)

    def _settle(self, judgments, response_json):
        from .agent_turn_service import _require_fresh_execution_append
        a = self.adapter
        execution = a._broker_execution()
        auth = next(e for e in execution.events if isinstance(e, ledger.ProviderAttemptAuthorizedEventV3)
                    and e.provider_attempt_id == a.last_provider_attempt_id)
        closure = selection.close_selection(self.catalog, judgments)
        event = ledger.BuildWriterEvidenceSelectionV1(kind="build_writer_evidence_selection_v1",
            event_id=uuid4(), sequence=len(execution.events), policy=selection.POLICY,
            mode="jev" if response_json is not None else "empty_catalog",
            controller_attempt_id=auth.provider_attempt_id, controller_envelope_sha256=auth.envelope_sha256,
            controller_response_sha256=hashlib.sha256(response_json.encode()).hexdigest() if response_json is not None else None,
            catalog_sha256=selection.digest(self.catalog), basis_sha256=self.state["basis_sha256"],
            terminal_disposition=self.terminal, judgments=judgments, **closure)
        proof = ({"request_json": self._prepared.body.decode(), "response_json": response_json}
                 if response_json is not None else None)
        a.turn = _require_fresh_execution_append(a.fence.append("record_build_writer_evidence_selection",
            "selection", event, producer_proof=proof))
        self.receipt = event
        return event
