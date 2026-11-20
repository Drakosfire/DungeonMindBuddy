"""Adapt legacy host-ID fixture replies to the model-facing alias contract."""

from copy import deepcopy
import json

from graph_memory.extraction.category_candidate_graph_extractor import FixtureCategoryGraphPassClient
from graph_memory.extraction.worldbuilding_prompt_aliases import WorldbuildingPromptAliases


def install_alias_fixture(monkeypatch):
    current = {}
    original_init = WorldbuildingPromptAliases.__init__
    original_run = FixtureCategoryGraphPassClient.run_pass

    def initialize(self, source_rows, *, nonce=None):
        original_init(self, source_rows, nonce="fixture")
        current["aliases"] = self

    def adapt(payload):
        aliases = current.get("aliases")
        if aliases is None:
            return payload
        value = deepcopy(payload)
        edge_to_handle = {value: key for key, value in aliases._handle_to_edge.items()}

        def visit(item):
            if isinstance(item, dict):
                span = item.get("source_span_ref_id")
                if isinstance(span, str) and span in aliases._span_to_handle:
                    item["source_span_ref_id"] = aliases._span_to_handle[span]
                for key in ("from_node_id", "to_node_id"):
                    if isinstance(item.get(key), str) and item[key] in aliases._node_to_handle:
                        item[key] = aliases._node_to_handle[item[key]]
                if isinstance(item.get("retained_edge_ids"), list):
                    item["retained_edge_ids"] = [edge_to_handle.get(v, v) if isinstance(v, str) else v
                                                 for v in item["retained_edge_ids"]]
                for nested in item.values():
                    visit(nested)
            elif isinstance(item, list):
                for nested in item:
                    visit(nested)
        visit(value)
        return value

    def run(self, name, **kwargs):
        result = original_run(self, name, **kwargs)
        result["parsed"] = adapt(result["parsed"])
        result["raw_text"] = json.dumps(result["parsed"])
        return result

    monkeypatch.setattr(WorldbuildingPromptAliases, "__init__", initialize)
    monkeypatch.setattr(FixtureCategoryGraphPassClient, "run_pass", run)
    return adapt
