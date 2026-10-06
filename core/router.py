from __future__ import annotations
import os
from typing import Any

try:
    from rapidfuzz import fuzz
    _HAS_FUZZ = True
except ImportError:
    import difflib
    _HAS_FUZZ = False

from core.schema import WorkflowDefinition


class WorkflowRouter:
    """Routes user requests to the appropriate workflow by matching the
    natural language query against workflow trigger and metadata keywords."""

    # Domain-specific keyword boosters for ambiguous workflows
    _KEYWORD_BOOSTS: dict[str, list[str]] = {
        "WF001": ["restock", "restocking", "stock", "inventory", "reorder", "low stock", "threshold"],
        "WF002": ["price", "vendor", "internal", "differs", "variance", "cost", "10%", "threshold", "validate", "pricing"],
        "WF003": ["vendor file", "process", "spreadsheet", "invalid", "clean", "normaliz"],
        "WF004": ["seo", "content", "description", "generate", "title", "meta", "marketing copy"],
        "WF005": ["order", "ord-", "status", "shipment", "tracking", "shipping", "where is"],
        "WF006": ["duplicate", "duplicat", "similar", "catalog", "same product"],
        "WF007": ["campaign", "brief", "collection", "promotion", "marketing campaign"],
        "WF008": ["keyword", "keywords", "classify", "seo keyword", "search intent"],
        "WF009": ["assign", "employee", "developer", "task", "workload", "skill"],
        "WF010": ["performance", "report", "failing", "fail", "error", "metric", "execution"],
    }

    def __init__(self, workflows: list[WorkflowDefinition]):
        self._workflows = workflows

    def route(self, query: str) -> tuple[WorkflowDefinition | None, float]:
        """Returns the best-matching workflow and its confidence score."""
        query_lower = query.lower()
        best_match = None
        best_score = 0.0

        for wf in self._workflows:
            combined = self._build_search_text(wf).lower()
            keyword_score = self._keyword_match(query_lower, combined)
            boost = self._keyword_boost(query_lower, wf.id)
            similarity = self._similarity(query_lower, combined)
            total = keyword_score * 0.5 + similarity * 0.2 + boost * 0.3
            if total > best_score:
                best_score = total
                best_match = wf

        if best_match and best_score > 0:
            return best_match, best_score
        return None, 0.0

    def _build_search_text(self, wf: WorkflowDefinition) -> str:
        """Combine all workflow metadata into a searchable string."""
        parts = [wf.name or "", wf.trigger or "", wf.inputs_description or ""]
        if wf.decision_logic:
            parts.append(wf.decision_logic)
        if wf.expected_output:
            parts.append(wf.expected_output)
        return " ".join(parts)

    def _keyword_boost(self, query: str, wf_id: str) -> float:
        """Apply a domain-specific keyword boost for the given workflow."""
        boosts = self._KEYWORD_BOOSTS.get(wf_id, [])
        score = 0.0
        for kw in boosts:
            if kw in query:
                score += 40
        return min(score, 100)

    @staticmethod
    def _keyword_match(query: str, text: str) -> float:
        """Score based on keyword overlap with partial matching."""
        query_words = set(w.strip(".,!?") for w in query.lower().split() if len(w) > 2)
        text_words = set(w.strip(".,!?").lower() for w in text.lower().split() if len(w) > 2)
        if not query_words:
            return 0.0
        overlap = 0
        for qw in query_words:
            for tw in text_words:
                if qw in tw or tw in qw:
                    overlap += 1
                    break
        return (overlap / len(query_words)) * 100

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        if _HAS_FUZZ:
            return fuzz.token_sort_ratio(a, b)
        else:
            return difflib.SequenceMatcher(None, a, b).ratio() * 100

    def get_workflow_by_id(self, wf_id: str) -> WorkflowDefinition | None:
        for wf in self._workflows:
            if wf.id == wf_id:
                return wf
        return None
