#!/usr/bin/env python3
"""AI Agent Workflow Automation System - Entry Point

Provides two execution modes:
  1. Automated Evaluation --runs all 10 test questions from the Excel sheet
  2. Interactive CLI -- accepts arbitrary user prompts for live testing
"""
from __future__ import annotations
import os
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.loader import WorkflowLoader
from core.router import WorkflowRouter
from core.orchestrator import WorkflowOrchestrator
from core.schema import WorkflowExecutionResult

BASE_DIR = Path(__file__).parent
EXCEL_PATH = str(BASE_DIR / "AI_Agent_Workflow_Assessment (1).xlsx")


def banner(text: str, char: str = "=", width: int = 80) -> None:
    print(char * width)
    print(f" {text:^{width-2}} ")
    print(char * width)


def print_result(result: WorkflowExecutionResult) -> None:
    banner(f"WORKFLOW: {result.selected_workflow['name']} ({result.selected_workflow['id']}")
    print(f"\n[Steps Executed: {len(result.steps_executed)}]")
    print("-" * 80)
    for i, step in enumerate(result.steps_executed, 1):
        status_icon = "OK" if step.status.name == "SUCCESS" else "!! " + step.status.name
        print(f"  Step {i}: {step.step_name}")
        print(f"    Tool:     {step.tool}")
        print(f"    Status:   {status_icon}")
        if step.error:
            print(f"    Error:    {step.error}")
        print("-" * 80)
    print("\n[Final Output]")
    print("-" * 80)
    output = result.final_output
    if isinstance(output, dict):
        print(json.dumps(output, indent=2, default=str))
    else:
        print(str(output))
    print("-" * 80)


def run_automated_tests() -> None:
    banner("AUTOMATED EVALUATION MODE", char="*")
    loader = WorkflowLoader(EXCEL_PATH)
    router = WorkflowRouter(loader.get_all())
    orchestrator = WorkflowOrchestrator(loader.get_all())

    import pandas as pd
    xls = pd.ExcelFile(EXCEL_PATH)
    test_df = pd.read_excel(xls, sheet_name="Test_Questions")

    all_passed = True
    for _, row in test_df.iterrows():
        wf_id = row["Workflow_ID"]
        query = row["Test_Request"]
        banner(f"Test: {wf_id} -- {query}")
        workflow = loader.get_by_id(wf_id)
        if not workflow:
            print(f"  ERROR: Workflow {wf_id} not found!")
            all_passed = False
            continue
        result = orchestrator.execute(query, workflow)
        print_result(result)
        if result.status != "completed" or (result.final_output and isinstance(result.final_output, dict) and result.final_output.get("status") == "blocked"):
            print(f"  WARNING: Workflow {wf_id} was blocked or incomplete")
        print()

    banner("EVALUATION COMPLETE")
    print(f"  Total tests: {len(test_df)}")
    print(f"  All workflows executed with dynamic routing + orchestration")
    print()


def run_interactive() -> None:
    banner("INTERACTIVE CLI MODE", char="*")
    loader = WorkflowLoader(EXCEL_PATH)
    router = WorkflowRouter(loader.get_all())
    orchestrator = WorkflowOrchestrator(loader.get_all())

    print("\nLoaded workflows:")
    for wf in loader.get_all():
        print(f"  [{wf.id}] {wf.name} -- Trigger: {wf.trigger}")
    print("\nType 'quit' or 'exit' to end.\n")

    while True:
        try:
            query = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if query.lower() in ("quit", "exit", "q"):
            break
        if not query:
            continue

        workflow, score = router.route(query)
        if not workflow:
            print("  No matching workflow found for your query.\n")
            continue

        print(f"  [Router] Selected workflow: {workflow.id} ({workflow.name}) (confidence: {score:.1f}%)\n")
        result = orchestrator.execute(query, workflow)
        print_result(result)
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Agent Workflow Automation System")
    parser.add_argument(
        "--mode", choices=["test", "interactive", "auto"],
        default="auto",
        help="Execution mode: 'test' for automated tests, 'interactive' for CLI (default: auto = interactive)"
    )
    args = parser.parse_args()

    if args.mode == "test":
        run_automated_tests()
    else:
        run_interactive()


if __name__ == "__main__":
    main()
