#!/usr/bin/env python3
"""Automated tests for all 10 workflow test questions from the Excel sheet.
Tests can run with or without pytest."""
from __future__ import annotations
import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from core.loader import WorkflowLoader
from core.router import WorkflowRouter
from core.orchestrator import WorkflowOrchestrator

BASE_DIR = Path(__file__).parent.parent
EXCEL_PATH = str(BASE_DIR / "AI_Agent_Workflow_Assessment (1).xlsx")


@pytest.fixture(scope="session")
def loader():
    return WorkflowLoader(EXCEL_PATH)


@pytest.fixture(scope="session")
def router(loader):
    return WorkflowRouter(loader.get_all())


@pytest.fixture(scope="session")
def orchestrator(loader):
    return WorkflowOrchestrator(loader.get_all())


WORKFLOW_TESTS = [
    ("WF001", "Which products need restocking?"),
    ("WF002", "Find products where vendor price differs by more than 10%."),
    ("WF003", "Process this vendor spreadsheet and show invalid rows."),
    ("WF004", "Generate SEO content for this product."),
    ("WF005", "Where is order ORD-1001?"),
    ("WF006", "Find likely duplicate products in the catalog."),
    ("WF007", "Create a campaign brief for the new collection."),
    ("WF008", "Classify these keywords and map them to pages."),
    ("WF009", "Assign this urgent task to the best available developer."),
    ("WF010", "Which workflows are failing most often?"),
]


@pytest.mark.parametrize("wf_id,query", WORKFLOW_TESTS)
def test_workflow_execution(loader, orchestrator, wf_id, query):
    """Each test verifies that a workflow from the Excel sheet runs end-to-end."""
    workflow = loader.get_by_id(wf_id)
    assert workflow is not None, f"Workflow {wf_id} not loaded from Excel"

    result = orchestrator.execute(query, workflow)

    assert result.selected_workflow["id"] == wf_id
    assert result.selected_workflow["name"] == workflow.name
    assert len(result.steps_executed) > 0, f"No steps executed for {wf_id}"
    assert result.final_output is not None, f"No final output for {wf_id}"

    print(f"\n[{wf_id}] {workflow.name}: PASSED")
    print(json.dumps(result.final_output, indent=2, default=str))


def test_router_selection(loader, router):
    """Verify the router selects the correct workflow for each test query."""
    for wf_id, query in WORKFLOW_TESTS:
        workflow, score = router.route(query)
        assert workflow is not None, f"Router returned no workflow for: {query}"
        assert workflow.id == wf_id, (
            f"Router selected {workflow.id} for '{query}', expected {wf_id}"
        )
        assert score > 0, f"Confidence score is 0 for query: {query}"


def test_all_workflows_loaded(loader):
    """Verify all 10 workflows are loaded from the Excel file."""
    workflows = loader.get_all()
    assert len(workflows) == 10, f"Expected 10 workflows, got {len(workflows)}"

    expected_ids = {f"WF{i:03d}" for i in range(1, 11)}
    actual_ids = {wf.id for wf in workflows}
    assert actual_ids == expected_ids, f"Workflow IDs mismatch: {actual_ids}"


def test_wf001_inventory_threshold(loader, orchestrator):
    """WF001: Verify restock threshold logic."""
    wf = loader.get_by_id("WF001")
    result = orchestrator.execute("Which products need restocking?", wf)
    output = result.final_output
    assert "restock_list" in output
    assert output["items_needing_restock"] >= 1, "Should find items needing restock"
    for item in output["restock_list"]:
        assert item["current_stock"] < item["minimum_stock"]
        assert item["reorder_quantity"] > 0


def test_wf002_price_validation(loader, orchestrator):
    """WF002: Verify price validation flagging."""
    wf = loader.get_by_id("WF002")
    result = orchestrator.execute("Find products where vendor price differs by more than 10%.", wf)
    output = result.final_output
    assert "exceptions" in output
    assert output["exception_count"] >= 1, "Should find at least one price exception >10%"


def test_wf003_vendor_file_validation(loader, orchestrator):
    """WF003: Verify missing field detection."""
    wf = loader.get_by_id("WF003")
    result = orchestrator.execute("Process this vendor spreadsheet and show invalid rows.", wf)
    output = result.final_output
    assert output["validation_summary"]["invalid_count"] >= 2, "Should find 2 invalid rows with missing fields"
    assert output["validation_summary"]["valid_count"] >= 1


def test_wf004_hallucination_prevention(loader, orchestrator):
    """WF004: Verify missing attributes are NOT invented."""
    wf = loader.get_by_id("WF004")
    result = orchestrator.execute("Generate SEO content for this product.", wf)
    output = result.final_output
    assert "long_description" in output or "short_description" in output
    if output.get("content_complete") is False:
        assert "HALLUCINATION_WARNING" in output, "Should flag missing fields without inventing"


def test_wf005_order_lookup(loader, orchestrator):
    """WF005: Verify order ORD-1001 is found with tracking."""
    wf = loader.get_by_id("WF005")
    result = orchestrator.execute("Where is order ORD-1001?", wf)
    output = result.final_output
    assert output.get("order_id") == "ORD-1001"
    assert "order_status" in output
    assert "shipment" in output


def test_wf006_duplicate_detection(loader, orchestrator):
    """WF006: Verify duplicate detection with SKU and fuzzy matching."""
    wf = loader.get_by_id("WF006")
    result = orchestrator.execute("Find likely duplicate products in the catalog.", wf)
    output = result.final_output
    assert "definite_duplicates" in output
    assert len(output["definite_duplicates"]) >= 1, "Should find at least one exact SKU duplicate"
    assert len(output["possible_duplicates"]) >= 1, "Should find at least one possible duplicate via similarity"


def test_wf007_campaign_gate(loader, orchestrator):
    """WF007: Verify gate blocks execution when dates/goal are missing."""
    wf = loader.get_by_id("WF007")
    result = orchestrator.execute("Create a campaign brief for the new collection.", wf)
    output = result.final_output
    assert output.get("status") == "blocked" or "escalated" in str(output).lower(), (
        "WF007 should block when required dates/goal are missing"
    )


def test_wf008_keyword_classification(loader, orchestrator):
    """WF008: Verify keyword classification with deduplication."""
    wf = loader.get_by_id("WF008")
    result = orchestrator.execute("Classify these keywords and map them to pages.", wf)
    output = result.final_output
    assert "classified_keywords" in output
    for kw, info in output["classified_keywords"].items():
        assert info["intent"] in ["Informational", "Commercial", "Transactional", "Navigational"]
        assert "target_page" in info


def test_wf009_employee_assignment(loader, orchestrator):
    """WF009: Verify employee ranking and task assignment."""
    wf = loader.get_by_id("WF009")
    result = orchestrator.execute("Assign this urgent task to the best available developer.", wf)
    output = result.final_output
    assert "assigned" in output
    if output.get("assigned"):
        assert "selected_employee" in output


def test_wf010_performance_report(loader, orchestrator):
    """WF010: Verify failure rate reporting."""
    wf = loader.get_by_id("WF010")
    result = orchestrator.execute("Which workflows are failing most often?", wf)
    output = result.final_output
    assert "analysis" in output
    for entry in output["analysis"]:
        assert "failure_rate_pct" in entry
        assert "flagged" in entry


def test_extensibility_wf011(loader, orchestrator):
    """Verify a dynamically added WF011 is auto-loaded and executable."""
    import pandas as pd
    df = pd.read_excel(EXCEL_PATH, sheet_name="Workflows")
    new_wf_row = {
        "Workflow_ID": "WF011",
        "Workflow_Name": "Customer Churn Risk Analysis",
        "Trigger": "User asks about customer churn risk",
        "Inputs": "Customer transaction data; engagement metrics",
        "Steps": "Load customer data \u2192 calculate churn risk \u2192 flag at-risk customers \u2192 summarize",
        "Decision_Logic": "Flag customers with churn risk > 50%",
        "Tools_Required": "CSV reader; calculator",
        "Expected_Output": "List of at-risk customers with churn probability scores"
    }
    df = pd.concat([df, pd.DataFrame([new_wf_row])], ignore_index=True)
    temp_excel = str(BASE_DIR / "data" / "_test_wf011.xlsx")
    temp_writer = pd.ExcelWriter(temp_excel, engine="openpyxl")
    df.to_excel(temp_writer, sheet_name="Workflows", index=False)
    temp_writer.close()
    try:
        new_loader = WorkflowLoader(temp_excel)
        wf = new_loader.get_by_id("WF011")
        assert wf is not None, "WF011 should be loaded after adding Excel row"
        assert wf.name == "Customer Churn Risk Analysis"
        print(f"\n[WF011] Extensibility test: PASSED - workflow loaded dynamically")
    finally:
        del new_loader
        if os.path.exists(temp_excel):
            try:
                os.remove(temp_excel)
            except PermissionError:
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
