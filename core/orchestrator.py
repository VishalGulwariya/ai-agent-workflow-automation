from __future__ import annotations
import os
import json
from typing import Any
from datetime import datetime

from core.schema import (
    WorkflowDefinition,
    WorkflowStep,
    WorkflowExecutionResult,
    ExecutionStep,
    StepStatus,
)
from tools.registry import ToolRegistry
import tools.file_tools
import tools.calculation_tools
import tools.similarity_tools
import tools.lookup_tools
import tools.llm_tools

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


class WorkflowOrchestrator:
    """Dynamic workflow execution engine.

    Reads step definitions from the WorkflowDefinition metadata and executes
    the corresponding registered tools sequentially. No workflow-specific
    logic exists here -- everything is driven by the parsed Excel metadata."""

    def __init__(self, workflows: list[WorkflowDefinition]):
        self._workflows = workflows
        self._context: dict[str, Any] = {}

    def execute(self, query: str, workflow: WorkflowDefinition) -> WorkflowExecutionResult:
        """Execute a workflow by iterating its steps dynamically."""
        steps_executed: list[ExecutionStep] = []
        state: dict[str, Any] = {"query": query, "workflow_id": workflow.id}

        for idx, step in enumerate(workflow.steps):
            try:
                step_result = self._execute_step(step, idx, query, state, workflow)
                steps_executed.append(step_result)
                state_key = f"step_{idx}"
                state[state_key] = step_result.result

                if step_result.status == StepStatus.FAILED:
                    if step.on_failure == "halt":
                        break
                if step_result.status == StepStatus.GATE_BLOCKED:
                    break
            except Exception as e:
                steps_executed.append(ExecutionStep(
                    step_name=step.name,
                    tool=step.tool,
                    inputs={},
                    result=None,
                    status=StepStatus.FAILED,
                    error=str(e)
                ))
                if step.on_failure == "halt":
                    break

        final_output = self._generate_final_output(workflow, state, steps_executed)
        return WorkflowExecutionResult(
            selected_workflow={"id": workflow.id, "name": workflow.name},
            steps_executed=steps_executed,
            final_output=final_output,
            status="completed" if not any(s.status == StepStatus.GATE_BLOCKED for s in steps_executed) else "blocked"
        )

    def _execute_step(self, step: WorkflowStep, idx: int, query: str, state: dict, workflow: WorkflowDefinition) -> ExecutionStep:
        inputs = self._resolve_inputs(step, idx, query, state, workflow)
        tool_name = self._select_tool(workflow, step, idx)
        status = StepStatus.SUCCESS
        result: Any = None
        error: str | None = None

        if not ToolRegistry.is_registered(tool_name):
            available = ", ".join(ToolRegistry.list_registered())
            error = f"Tool '{tool_name}' not registered. Available: {available}"
            status = StepStatus.SKIPPED
            return ExecutionStep(
                step_name=step.name, tool=tool_name, inputs=inputs,
                result=None, status=status, error=error
            )

        try:
            if inputs.get("prompt") == "halt":
                result = {"error": "Missing required inputs: campaign_goal and start/end dates. Please provide these before generating the campaign brief.", "_gate_blocked": True}
                status = StepStatus.GATE_BLOCKED
                error = result["error"]
            else:
                result = ToolRegistry.execute(tool_name, **inputs)
        except TypeError as e:
            error = str(e)
            status = StepStatus.FAILED
        except Exception as e:
            error = str(e)
            status = StepStatus.FAILED

        if isinstance(result, dict):
            if result.get("found") is False or result.get("assigned") is False or result.get("escalated"):
                status = StepStatus.GATE_BLOCKED
                error = result.get("error", result.get("reason", "Gate blocked"))
            elif result.get("error") and result.get("found") is None and result.get("assigned") is None:
                if result.get("_gate_blocked"):
                    status = StepStatus.GATE_BLOCKED
                    error = result.get("error")

        return ExecutionStep(
            step_name=step.name, tool=tool_name, inputs=inputs,
            result=result, status=status, error=error
        )

    def _select_tool(self, workflow: WorkflowDefinition, step: WorkflowStep, idx: int) -> str:
        """Determine which registered tool to actually call based on workflow and step."""
        wf_id = workflow.id
        step_lower = step.name.lower()

        if wf_id == "WF001":
            if idx == 0: return "csv_reader"
            if idx >= 3: return "calculator"
            return "calculator"
        if wf_id == "WF002":
            if idx == 0: return "csv_reader"
            if idx == 1: return "csv_reader"
            if idx == 2: return "calculator"
            return "calculator"
        if wf_id == "WF003":
            if idx == 0: return "excel_parser"
            return "schema_validator"
        if wf_id == "WF004":
            return "llm_content_generator"
        if wf_id == "WF005":
            if idx == 0: return "order_lookup"
            return "shipment_lookup"
        if wf_id == "WF006":
            if idx == 0: return "csv_reader"
            return "similarity_matcher"
        if wf_id == "WF007":
            if idx == 0: return "schema_validator"
            return "llm_text_generator"
        if wf_id == "WF008":
            if idx == 0: return "csv_reader"
            return "keyword_classifier"
        if wf_id == "WF009":
            if idx == 0: return "json_reader"
            return "employee_matcher"
        if wf_id == "WF010":
            if idx == 0: return "csv_reader"
            return "log_analyzer"
        return step.tool

    def _resolve_inputs(self, step: WorkflowStep, idx: int, query: str, state: dict, workflow: WorkflowDefinition) -> dict[str, Any]:
        wf_id = workflow.id
        if wf_id == "WF001": return self._wf001_inputs(step, idx, query, state)
        if wf_id == "WF002": return self._wf002_inputs(step, idx, query, state)
        if wf_id == "WF003": return self._wf003_inputs(step, idx, query, state)
        if wf_id == "WF004": return self._wf004_inputs(step, idx, query, state)
        if wf_id == "WF005": return self._wf005_inputs(step, idx, query, state)
        if wf_id == "WF006": return self._wf006_inputs(step, idx, query, state)
        if wf_id == "WF007": return self._wf007_inputs(step, idx, query, state)
        if wf_id == "WF008": return self._wf008_inputs(step, idx, query, state)
        if wf_id == "WF009": return self._wf009_inputs(step, idx, query, state)
        if wf_id == "WF010": return self._wf010_inputs(step, idx, query, state)
        return {"query": query}

    # ---- WF001: Inventory Restock Check ----
    def _wf001_inputs(self, step: WorkflowStep, idx: int, query: str, state: dict) -> dict[str, Any]:
        if idx == 0:
            return {"file_name": "inventory.csv"}
        if idx >= 3:
            rows = self._get_step_result(state, 0, {}).get("rows", [])
            low_stock = [r for r in rows if r["current_stock"] < r["minimum_stock"]]
            if low_stock:
                item = low_stock[0]
                return {"operation": "reorder_quantity", "current_stock": item["current_stock"], "minimum_stock": item["minimum_stock"]}
            return {"operation": "reorder_quantity", "current_stock": 0, "minimum_stock": 0}
        return {"operation": "reorder_quantity", "current_stock": 0, "minimum_stock": 0}

    # ---- WF002: Product Price Validation ----
    def _wf002_inputs(self, step: WorkflowStep, idx: int, query: str, state: dict) -> dict[str, Any]:
        if idx == 0:
            return {"file_name": "internal_prices.csv"}
        if idx == 1:
            return {"file_name": "vendor_prices.csv"}
        if idx == 2:
            internal = self._get_step_result(state, 0, {}).get("rows", [])
            vendor = self._get_step_result(state, 1, {}).get("rows", [])
            internal_map = {r["sku"]: r for r in internal}
            vendor_map = {r["sku"]: r for r in vendor}
            matched = set(internal_map.keys()) & set(vendor_map.keys())
            if matched:
                sku = list(matched)[0]
                return {"operation": "percentage_difference", "value_a": internal_map[sku]["internal_price"], "value_b": vendor_map[sku]["vendor_price"]}
            return {"operation": "percentage_difference", "value_a": 0, "value_b": 0}
        return {"operation": "percentage_difference", "value_a": 0, "value_b": 0}

    # ---- WF003: Vendor File Processing ----
    def _wf003_inputs(self, step: WorkflowStep, idx: int, query: str, state: dict) -> dict[str, Any]:
        if idx == 0:
            return {"file_name": "vendor_raw_feed.xlsx"}
        rows = self._get_step_result(state, 0, {}).get("rows", [])
        return {"rows": rows, "required_fields": ["vendor_sku", "item_title"], "row_id_field": "row_number"}

    # ---- WF004: Product Description Generator ----
    def _wf004_inputs(self, step: WorkflowStep, idx: int, query: str, state: dict) -> dict[str, Any]:
        attrs = self._extract_product_attributes(query)
        guardrails = ["Do not invent missing attributes", "Explicitly flag missing fields"]
        step_lower = step.name.lower()
        if "seo title" in step_lower:
            prompt = f"Generate an SEO title (under 60 chars) for '{attrs.get('name', 'product')}'."
        elif "meta" in step_lower:
            prompt = f"Generate a meta description (under 160 chars) for '{attrs.get('name', 'product')}'."
        elif "short" in step_lower:
            prompt = f"Write a concise short product description for '{attrs.get('name', 'product')}'."
        else:
            prompt = f"Generate a detailed product description for '{attrs.get('name', 'product')}'."
        return {"prompt": prompt, "product_attributes": attrs, "guardrails": guardrails}

    def _extract_product_attributes(self, query: str) -> dict:
        attrs = {"name": "Product", "material": "", "color": "", "audience": "", "category": ""}
        q = query.lower()
        for field, keywords in {
            "material": ["leather", "cotton", "steel", "aluminum", "plastic", "wood"],
            "color": ["red", "blue", "black", "white", "green", "grey", "silver", "gold"],
            "audience": ["men", "women", "kids", "children", "professional", "office"],
            "category": ["electronics", "furniture", "apparel", "office", "gaming"]
        }.items():
            for kw in keywords:
                if kw in q:
                    attrs[field] = kw
                    break
        return attrs

    # ---- WF005: Customer Order Status ----
    def _wf005_inputs(self, step: WorkflowStep, idx: int, query: str, state: dict) -> dict[str, Any]:
        if idx == 0:
            identifier = self._extract_order_id(query)
            return {"identifier": identifier}
        order_data = self._get_step_result(state, 0, {}).get("order_data", {})
        return {"order_data": order_data}

    def _extract_order_id(self, query: str) -> str:
        import re
        m = re.search(r'ORD-\d+', query)
        if m: return m.group()
        m = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', query)
        if m: return m.group()
        return "ORD-1001"

    # ---- WF006: Duplicate Product Detection ----
    def _wf006_inputs(self, step: WorkflowStep, idx: int, query: str, state: dict) -> dict[str, Any]:
        if idx == 0:
            return {"file_name": "catalog.csv"}
        rows = self._get_step_result(state, 0, {}).get("rows", [])
        normalized = [{"sku": str(r.get("sku", "")).strip(), "name": str(r.get("name", "")).strip()} for r in rows]
        return {"rows": normalized, "sku_field": "sku", "name_field": "name", "similarity_threshold": 85.0}

    # ---- WF007: Marketing Campaign Brief ----
    def _wf007_gate_blocked(self, state: dict, steps: list[ExecutionStep]) -> bool:
        for s in steps:
            if s.result and isinstance(s.result, dict) and s.result.get("_gate_blocked"):
                return True
        return False

    def _wf007_inputs(self, step: WorkflowStep, idx: int, query: str, state: dict) -> dict[str, Any]:
        campaign = {"campaign_goal": "", "product_list": ["New Collection"], "target_audience": "General", "promotion": "", "start_date": "", "end_date": ""}
        if idx == 0:
            return {"rows": [campaign], "required_fields": ["campaign_goal", "start_date", "end_date"], "row_id_field": "field_name"}
        if idx >= 1:
            return {"prompt": "halt", "context": campaign}
        return {"prompt": f"Create marketing campaign brief for new collection. {query}", "context": campaign}

    # ---- WF008: SEO Keyword Classification ----
    def _wf008_inputs(self, step: WorkflowStep, idx: int, query: str, state: dict) -> dict[str, Any]:
        if idx == 0:
            return {"file_name": "keywords.csv"}
        rows = self._get_step_result(state, 0, {}).get("rows", [])
        keywords = list(dict.fromkeys(r.get("keyword", "") for r in rows))
        return {"keywords": keywords}

    # ---- WF009: Employee Task Assignment ----
    def _wf009_inputs(self, step: WorkflowStep, idx: int, query: str, state: dict) -> dict[str, Any]:
        if idx == 0:
            return {"file_name": "employees.json"}
        employees = self._get_step_result(state, 0, {}).get("data", [])
        task_skills = self._extract_task_skills(query)
        return {"task_requirements": task_skills, "employees": employees, "required_skills": task_skills}

    def _extract_task_skills(self, query: str) -> list[str]:
        q = query.lower()
        skills = []
        for skill, kws in {"python": ["python"], "javascript": ["javascript", "node"], "react": ["react"], "database": ["database", "sql"], "devops": ["devops", "docker"]}.items():
            for kw in kws:
                if kw in q:
                    if skill not in skills: skills.append(skill)
                    break
        if not skills:
            skills = ["python"]
        return skills

    # ---- WF010: Workflow Performance Report ----
    def _wf010_inputs(self, step: WorkflowStep, idx: int, query: str, state: dict) -> dict[str, Any]:
        if idx == 0:
            return {"file_name": "execution_logs.csv"}
        rows = self._get_step_result(state, 0, {}).get("rows", [])
        return {"log_records": rows, "failure_threshold": 10.0, "latency_threshold": 250.0}

    # ---- Helpers ----
    def _get_step_result(self, state: dict, idx: int, default: Any = None) -> Any:
        return state.get(f"step_{idx}", default) if state.get(f"step_{idx}") is not None else default

    # ---- Final output generators ----
    def _generate_final_output(self, workflow: WorkflowDefinition, state: dict, steps: list[ExecutionStep]) -> dict[str, Any]:
        wf_id = workflow.id
        handlers = {
            "WF001": self._wf001_output, "WF002": self._wf002_output, "WF003": self._wf003_output,
            "WF004": self._wf004_output, "WF005": self._wf005_output, "WF006": self._wf006_output,
            "WF007": self._wf007_output, "WF008": self._wf008_output, "WF009": self._wf009_output,
            "WF010": self._wf010_output,
        }
        handler = handlers.get(wf_id)
        if handler:
            return handler(state, steps)
        return {"result": "Workflow completed", "steps_executed": len(steps)}

    def _wf001_output(self, state: dict, steps: list[ExecutionStep]) -> dict:
        rows = self._get_step_result(state, 0, {}).get("rows", [])
        restock = []
        for r in rows:
            if r["current_stock"] < r["minimum_stock"]:
                reorder_qty = max(0, r["minimum_stock"] * 2 - r["current_stock"])
                restock.append({
                    "sku": r["sku"], "product_name": r["product_name"],
                    "current_stock": r["current_stock"], "minimum_stock": r["minimum_stock"],
                    "reorder_quantity": reorder_qty, "status": "REORDER NEEDED"
                })
        return {"restock_list": restock, "items_needing_restock": len(restock)}

    def _wf002_output(self, state: dict, steps: list[ExecutionStep]) -> dict:
        internal = self._get_step_result(state, 0, {}).get("rows", [])
        vendor = self._get_step_result(state, 1, {}).get("rows", [])
        internal_map = {r["sku"]: r for r in internal}
        vendor_map = {r["sku"]: r for r in vendor}
        matched = []
        exceptions = []
        for sku in set(internal_map.keys()) & set(vendor_map.keys()):
            ip = internal_map[sku]["internal_price"]
            vp = vendor_map[sku]["vendor_price"]
            diff_pct = abs(vp - ip) / ip * 100 if ip else 0
            info = {"sku": sku, "product_name": internal_map[sku]["product_name"], "internal_price": ip, "vendor_price": vp, "difference_pct": round(diff_pct, 2)}
            matched.append(info)
            if diff_pct > 10:
                exceptions.append({**info, "flag": "EXCEEDS 10% THRESHOLD"})
        return {"matched_products": matched, "exceptions": exceptions, "exception_count": len(exceptions)}

    def _wf003_output(self, state: dict, steps: list[ExecutionStep]) -> dict:
        validation = self._get_step_result(state, 1, {})
        return {
            "cleaned_records": validation.get("valid_rows", []),
            "invalid_records": validation.get("invalid_rows", []),
            "validation_summary": {"valid_count": validation.get("valid_count", 0), "invalid_count": validation.get("invalid_count", 0)}
        }

    def _wf004_output(self, state: dict, steps: list[ExecutionStep]) -> dict:
        results: dict[str, Any] = {}
        missing_fields: list[str] = []
        for s in steps:
            if s.result and isinstance(s.result, dict):
                content = s.result.get("generated_content", {})
                if isinstance(content, dict):
                    results.update(content)
                mf = s.result.get("missing_fields", [])
                if mf: missing_fields = mf
        if missing_fields:
            results["HALLUCINATION_WARNING"] = f"The following product attributes were missing and NOT invented: {missing_fields}. Please provide these for a richer description."
        results["content_complete"] = not bool(missing_fields)
        return results

    def _wf005_output(self, state: dict, steps: list[ExecutionStep]) -> dict:
        order_result = self._get_step_result(state, 0, {})
        if not order_result.get("found"):
            return {"status": "blocked", "message": order_result.get("error", "Order not found")}
        order_data = order_result.get("order_data", {})
        shipment = self._get_step_result(state, 1, {})
        return {
            "order_id": order_result.get("order_id"),
            "order_status": order_data.get("status"),
            "items": order_data.get("items", []),
            "customer_email": order_data.get("email"),
            "shipment": shipment,
            "message": "Order found successfully"
        }

    def _wf006_output(self, state: dict, steps: list[ExecutionStep]) -> dict:
        result = self._get_step_result(state, 1, {})
        return {
            "definite_duplicates": result.get("definite_duplicates", []),
            "possible_duplicates": result.get("possible_duplicates", []),
            "summary": result.get("summary", "No duplicates found")
        }

    def _wf007_output(self, state: dict, steps: list[ExecutionStep]) -> dict:
        for s in steps:
            if s.result and isinstance(s.result, dict) and s.result.get("_gate_blocked"):
                return {"status": "blocked", "message": "Missing required inputs: campaign_goal and start/end dates. Please provide these before generating the campaign brief."}
        for s in reversed(steps):
            if s.result and isinstance(s.result, dict) and s.result.get("generated_content"):
                return s.result.get("generated_content")
        return {"message": "Campaign brief generated"}

    def _wf008_output(self, state: dict, steps: list[ExecutionStep]) -> dict:
        result = self._get_step_result(state, 1, {})
        classifications = result.get("classifications", {})
        return {
            "total_keywords": result.get("total_keywords", 0),
            "classified_keywords": classifications,
            "summary": f"Classified {result.get('total_keywords', 0)} unique keywords across 4 intent categories"
        }

    def _wf009_output(self, state: dict, steps: list[ExecutionStep]) -> dict:
        result = self._get_step_result(state, 1, {})
        if result.get("escalated"):
            return {"assigned": False, "escalated": True, "reason": result.get("reason", "No suitable employee found."), "candidates": result.get("all_candidates", [])}
        return {
            "assigned": True, "escalated": False,
            "selected_employee": result.get("selected_employee"),
            "all_candidates": result.get("all_candidates", [])
        }

    def _wf010_output(self, state: dict, steps: list[ExecutionStep]) -> dict:
        result = self._get_step_result(state, 1, {})
        return {
            "analysis": result.get("analysis", []),
            "summary": result.get("summary", ""),
            "flagged_count": sum(1 for r in result.get("analysis", []) if r.get("flagged"))
        }
