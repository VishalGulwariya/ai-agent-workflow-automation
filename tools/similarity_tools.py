from __future__ import annotations
from typing import Any

from tools.registry import ToolRegistry

try:
    from rapidfuzz import fuzz
    _HAS_RAPIDFUZZ = True
except ImportError:
    import difflib
    _HAS_RAPIDFUZZ = False


@ToolRegistry.register("similarity_matcher", "Compares product SKUs and names to detect duplicates")
def similarity_matcher(rows: list[dict], sku_field: str = "sku", name_field: str = "name", similarity_threshold: float = 85.0) -> dict[str, Any]:
    if isinstance(rows, str):
        import json
        rows = json.loads(rows)
    seen_skus: dict[str, list[int]] = {}
    for i, row in enumerate(rows):
        sku = str(row.get(sku_field, "")).strip()
        if sku:
            seen_skus.setdefault(sku, []).append(i)
    definite_duplicates = []
    for sku, indices in seen_skus.items():
        if len(indices) > 1:
            definite_duplicates.append({
                "sku": sku,
                "confidence": 100,
                "duplicate_indices": indices,
                "type": "Exact SKU Match"
            })
    possible_duplicates = []
    checked_pairs = set()
    for i, row_i in enumerate(rows):
        for j, row_j in enumerate(rows):
            if i >= j:
                pair = (i, j)
                if pair in checked_pairs:
                    continue
                checked_pairs.add(pair)
            name_i = str(row_i.get(name_field, ""))
            name_j = str(row_j.get(name_field, ""))
            if name_i and name_j and i != j:
                score = _compute_similarity(name_i, name_j)
                if score >= similarity_threshold:
                    sku_i = str(row_i.get(sku_field, ""))
                    sku_j = str(row_j.get(sku_field, ""))
                    if sku_i != sku_j:
                        possible_duplicates.append({
                            "indices": [i, j],
                            "confidence": round(score, 2),
                            "type": "Possible Duplicate - High Attribute Similarity"
                        })
    return {
        "definite_duplicates": definite_duplicates,
        "possible_duplicates": possible_duplicates,
        "total_checked": len(rows),
        "summary": f"Found {len(definite_duplicates)} definite and {len(possible_duplicates)} possible duplicates"
    }


def _compute_similarity(a: str, b: str) -> float:
    if _HAS_RAPIDFUZZ:
        return fuzz.ratio(a, b)
    else:
        return difflib.SequenceMatcher(None, a, b).ratio() * 100
