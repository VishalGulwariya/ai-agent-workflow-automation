from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any, Optional
from enum import Enum
import enum


class StepStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    GATE_BLOCKED = "gate_blocked"


class StepType(str, enum.Enum):
    TOOL_CALL = "tool_call"
    GATE = "gate"
    LLM_CALL = "llm_call"
    TRANSFORM = "transform"


class WorkflowStep(BaseModel):
    order: int
    name: str
    tool: str
    description: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    conditions: list[str] = Field(default_factory=list)
    on_failure: str = "halt"
    decision_logic: Optional[str] = None
    decision_threshold: Optional[float] = None


class WorkflowDefinition(BaseModel):
    id: str
    name: str
    trigger: str
    inputs_description: str
    steps: list[WorkflowStep] = Field(default_factory=list)
    decision_logic: Optional[str] = None
    tools_required: list[str] = Field(default_factory=list)
    expected_output: Optional[str] = None


class ExecutionStep(BaseModel):
    step_name: str
    tool: str
    inputs: dict[str, Any]
    result: Any
    status: StepStatus
    error: Optional[str] = None


class WorkflowExecutionResult(BaseModel):
    selected_workflow: dict[str, str]
    steps_executed: list[ExecutionStep]
    final_output: Any
    status: str = "completed"
    error: Optional[str] = None
