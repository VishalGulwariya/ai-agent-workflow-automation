from __future__ import annotations
from typing import Any
import math

from tools.registry import ToolRegistry


@ToolRegistry.register("calculator", "General-purpose calculator for reordering, metrics, and arithmetic")
def calculator(operation: str, **kwargs) -> Any:
    if operation == "reorder_quantity":
        current = kwargs.get("current_stock", 0)
        minimum = kwargs.get("minimum_stock", 0)
        return max(0, minimum * 2 - current)
    if operation == "percentage_difference":
        a = kwargs.get("value_a", 0)
        b = kwargs.get("value_b", 0)
        if a == 0:
            return float("inf") if b != 0 else 0.0
        return abs(a - b) / a * 100
    if operation == "mean":
        values = kwargs.get("values", [])
        if not values:
            return 0
        return sum(values) / len(values)
    if operation == "rate":
        total = kwargs.get("total", 0)
        failures = kwargs.get("failures", 0)
        if total == 0:
            return 0.0
        return failures / total
    if operation == "threshold_check":
        value = kwargs.get("value", 0)
        threshold = kwargs.get("threshold", 0)
        return value > threshold
    if operation == "add":
        return kwargs.get("a", 0) + kwargs.get("b", 0)
    if operation == "subtract":
        return kwargs.get("a", 0) - kwargs.get("b", 0)
    if operation == "compare":
        a = kwargs.get("a", 0)
        b = kwargs.get("b", 0)
        threshold = kwargs.get("threshold", 0)
        diff_pct = abs(a - b) / a * 100 if a != 0 else float("inf")
        return {"difference_pct": diff_pct, "exceeds_threshold": diff_pct > threshold}
    if operation == "capacity":
        max_cap = kwargs.get("max_capacity", 0)
        current = kwargs.get("current_active_tasks", 0)
        return max_cap - current
    if operation == "aggregate_logs":
        records = kwargs.get("records", [])
        total = len(records)
        failures = sum(1 for r in records if r.get("status") != "SUCCESS")
        times = [r.get("time_ms", 0) for r in records]
        avg_time = sum(times) / len(times) if times else 0
        return {
            "total_executions": total,
            "failures": failures,
            "failure_rate": failures / total if total else 0,
            "avg_execution_time_ms": avg_time
        }
    raise ValueError(f"Unknown operation: {operation}")


@ToolRegistry.register("log_analyzer", "Aggregates log records to compute failure rates and average execution times")
def log_analyzer(log_records: list[dict], failure_threshold: float = 10.0, latency_threshold: float = 250.0) -> dict[str, Any]:
    if isinstance(log_records, str):
        import json
        log_records = json.loads(log_records)
    by_workflow: dict[str, list[dict]] = {}
    for rec in log_records:
        wid = rec.get("workflow_id", "UNKNOWN")
        by_workflow.setdefault(wid, []).append(rec)
    results = []
    for wid, records in by_workflow.items():
        total = len(records)
        failures = sum(1 for r in records if r.get("status") != "SUCCESS")
        times = [r.get("time_ms", 0) for r in records]
        avg_time = sum(times) / len(times) if times else 0
        failure_rate = failures / total * 100 if total else 0
        flagged = failure_rate > failure_threshold or avg_time > latency_threshold
        results.append({
            "workflow_id": wid,
            "total_executions": total,
            "failures": failures,
            "failure_rate_pct": round(failure_rate, 2),
            "avg_execution_time_ms": round(avg_time, 2),
            "flagged": flagged,
            "flag_reason": (
                "failure_rate_exceeded" if failure_rate > failure_threshold else
                "latency_exceeded" if avg_time > latency_threshold else None
            )
        })
    return {"analysis": results, "summary": f"{sum(1 for r in results if r['flagged'])} workflow(s) flagged for review"}


@ToolRegistry.register("keyword_classifier", "Classifies keywords into search intent categories and maps to target pages")
def keyword_classifier(keywords: list[str], classifications: str | dict | None = None) -> dict[str, Any]:
    if isinstance(classifications, str):
        import json
        classifications = json.loads(classifications)
    if isinstance(classifications, dict):
        return {"classifications": classifications, "total": len(classifications)}
    intent_map = {}
    url_category_map = {
        "Informational": "/guides",
        "Commercial": "/category",
        "Transactional": "/shop",
        "Navigational": "/account"
    }
    for kw in keywords:
        lower = kw.lower().strip()
        if "buy" in lower or "price" in lower or "cheap" in lower or "discount" in lower:
            intent = "Transactional"
        elif "how" in lower or "what" in lower or "guide" in lower or "tips" in lower:
            intent = "Informational"
        elif "best" in lower or "review" in lower or "compare" in lower:
            intent = "Commercial"
        elif "login" in lower or "account" in lower or lower in ("home", "shop"):
            intent = "Navigational"
        else:
            intent = "Commercial"
        priority = "High" if intent in ("Transactional", "Commercial") else "Medium"
        if lower in intent_map:
            intent_map[lower]["count"] += 1
        else:
            intent_map[lower] = {"intent": intent, "target_page": url_category_map[intent], "priority": priority, "count": 1}
    return {"classifications": intent_map, "total_keywords": len(intent_map), "total_occurrences": sum(v["count"] for v in intent_map.values())}
