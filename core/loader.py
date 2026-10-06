from __future__ import annotations
import pandas as pd
import re
from typing import Any
from core.schema import WorkflowDefinition, WorkflowStep


class WorkflowLoader:
    """Loads workflow definitions dynamically from an Excel file.
    Each row in the 'Workflows' sheet becomes a WorkflowDefinition object.
    Adding a new row (e.g. WF011) automatically creates a new workflow
    without any code changes to the orchestrator."""

    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self._workflows: list[WorkflowDefinition] = []
        self._load()

    def _load(self) -> None:
        xls = pd.ExcelFile(self.excel_path)
        workflows_df = pd.read_excel(xls, sheet_name="Workflows")
        for _, row in workflows_df.iterrows():
            wf_id = row.get("Workflow_ID", "")
            wf_name = row.get("Workflow_Name", "")
            trigger = row.get("Trigger", "")
            inputs_desc = row.get("Inputs", "")
            steps_raw = row.get("Steps", "")
            decision_logic = row.get("Decision_Logic", "")
            tools_raw = row.get("Tools_Required", "")
            expected_output = row.get("Expected_Output", "")

            tools = self._parse_tools(tools_raw)
            steps = self._parse_steps(steps_raw, tools, decision_logic)

            self._workflows.append(WorkflowDefinition(
                id=wf_id,
                name=wf_name,
                trigger=trigger,
                inputs_description=inputs_desc,
                steps=steps,
                decision_logic=decision_logic,
                tools_required=tools,
                expected_output=expected_output
            ))

    def _parse_tools(self, raw: str) -> list[str]:
        if not isinstance(raw, str) or not raw.strip():
            return []
        return [t.strip().lower().replace(" ", "_").replace("/", "_") for t in raw.split(";") if t.strip()]

    def _parse_steps(self, raw: str, tools: list[str], decision_logic: str) -> list[WorkflowStep]:
        """Convert the human-readable step string into structured WorkflowStep objects.
        Maps natural language steps to registered tool names dynamically."""
        if not isinstance(raw, str) or not raw.strip():
            return []
        raw_steps = [s.strip() for s in raw.split("→") if s.strip()]
        parsed: list[WorkflowStep] = []
        for i, step_text in enumerate(raw_steps, 1):
            tool_name = self._map_step_to_tool(step_text, tools)
            parsed.append(WorkflowStep(
                order=i,
                name=step_text,
                tool=tool_name,
                description=step_text,
                decision_logic=decision_logic if i == len(raw_steps) else None
            ))
        return parsed

    @staticmethod
    def _map_step_to_tool(step_text: str, declared_tools: list[str]) -> str:
        """Map natural language step descriptions to actual registered tool function names.
        Uses keyword matching against known tool capabilities, then falls back
        to declared tools in order (normalised to registered naming)."""
        lower = step_text.lower()
        tool_map = [
            ("read keywords", "csv_reader"),
            ("read file", "csv_reader"),
            ("read file", "excel_parser"),
            ("normalize", "schema_validator"),
            ("validate", "schema_validator"),
            ("invalid rows", "schema_validator"),
            ("cleaned dataset", "schema_validator"),
            ("load inventory", "csv_reader"),
            ("load product", "csv_reader"),
            ("load employees", "json_reader"),
            ("load execution", "csv_reader"),
            ("read order", "order_lookup"),
            ("search order", "order_lookup"),
            ("retrieve shipment", "shipment_lookup"),
            ("shipment", "shipment_lookup"),
            ("compare internal and vendor", "calculator"),
            ("percentage difference", "calculator"),
            ("calculate reorder", "calculator"),
            ("compute reorder", "calculator"),
            ("compute", "calculator"),
            ("calculate", "calculator"),
            ("aggregate", "log_analyzer"),
            ("log", "log_analyzer"),
            ("similarity", "similarity_matcher"),
            ("duplicate", "similarity_matcher"),
            ("classify", "keyword_classifier"),
            ("rank", "employee_matcher"),
            ("match employee", "employee_matcher"),
            ("assign", "employee_matcher"),
            ("generate seo", "llm_content_generator"),
            ("create product", "llm_text_generator"),
            ("create messaging", "llm_text_generator"),
            ("create channel", "llm_text_generator"),
            ("create campaign", "llm_text_generator"),
            ("generate", "llm_content_generator"),
            ("create", "llm_text_generator"),
            ("load customer", "csv_reader"),
            ("flag at-risk", "calculator"),
        ]
        for keyword, tool_name in tool_map:
            if keyword in lower:
                return tool_name
        if declared_tools:
            normalised = [t.replace(" ", "_") for t in declared_tools]
            for norm in normalised:
                if "csv" in norm:
                    return "csv_reader"
                if "excel" in norm:
                    return "excel_parser"
                if "validator" in norm or "valid" in norm:
                    return "schema_validator"
                if "calculat" in norm or "math" in norm:
                    return "calculator"
                if "llm" in norm or "text" in norm:
                    return "llm_text_generator"
                if "similarity" in norm:
                    return "similarity_matcher"
                if "duplicate" in norm:
                    return "similarity_matcher"
                if "lookup" in norm:
                    return "order_lookup"
                if "rank" in norm or "match" in norm:
                    return "employee_matcher"
                if "log" in norm:
                    return "log_analyzer"
                if "classify" in norm:
                    return "keyword_classifier"
            return normalised[0]
        return step_text.replace(" ", "_").lower()

    @property
    def workflows(self) -> list[WorkflowDefinition]:
        return self._workflows

    def get_by_id(self, wf_id: str) -> WorkflowDefinition | None:
        for wf in self._workflows:
            if wf.id == wf_id:
                return wf
        return None

    def get_all(self) -> list[WorkflowDefinition]:
        return self._workflows
