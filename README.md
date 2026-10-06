# AI Agent Workflow Automation System

A metadata-driven, multi-workflow AI agent orchestration engine in Python. The system dynamically ingests business workflows from an Excel file and routes natural-language user prompts to the appropriate workflow—**no hard-coded workflow logic in the orchestrator**.

> **Key Principle:** Adding a new workflow (e.g., WF011) requires only adding a row to the Excel file—no code changes inside `core/`, `tools/`, or `main.py`.

## Architecture

```
User Request
      │
      ▼
┌──────────────────┐    Loads Excel at startup
│  WorkflowLoader  │    Parses each row → WorkflowDefinition (Pydantic)
└────────┬─────────┘
      │ Workflows metadata (steps, triggers, tools, gates)
      ▼
┌────────┴─────────┐    Keyword + fuzzy match
│  WorkflowRouter  │    → selects best workflow
└────────┬─────────┘
      │ Selected workflow specification
      ▼
┌────────┴─────────┐    Iterates steps dynamically
│   Orchestrator   │    Looks up tool by name from registry
└────┬─────────┬───┘    Executes tool → updates context → checks gates
      │         │
      ▼         ▼
┌──────────┐  ┌──────────┐
│ Tool     │  │ Decision │
│ Registry │  │ / Gate   │
│  (CSV,   │  │  Logic   │
│   Calc,  │  │          │
│   LLM)   │  │          │
└──────────┘  ┌──────────┘
      │         │
      ▼         ▼
┌──────────────────────────┐
│  Structured Output       │
│  - selected_workflow     │
│  - steps_executed        │
│  - final_output          │
└──────────────────────────┘
```

## Project Structure

```text
ai_agent_workflows/
├── README.md
├── requirements.txt
├── .env.example
├── main.py                        # CLI entry point (test + interactive modes)
├── AI_Agent_Workflow_Assessment (1).xlsx
├── core/
│   ├── __init__.py
│   ├── schema.py                  # Pydantic models: WorkflowDefinition, ExecutionResult
│   ├── loader.py                  # Excel → WorkflowDefinition parser
│   ├── router.py                  # Intent classification / workflow selection
│   └── orchestrator.py            # Generic dynamic workflow engine
├── tools/
│   ├── __init__.py
│   ├── registry.py                # @register_tool decorator + ToolRegistry
│   ├── file_tools.py              # CSV reader, Excel parser, schema validator
│   ├── calculation_tools.py       # Calculator, log analyzer, keyword classifier
│   ├── similarity_tools.py        # Fuzzy matching (rapidfuzz)
│   ├── lookup_tools.py            # Order/shipment lookup, employee matching
│   └── llm_tools.py               # LLM content generator (mock mode supported)
├── data/
│   ├── inventory.csv              # WF001
│   ├── internal_prices.csv        # WF002
│   ├── vendor_prices.csv          # WF002
│   ├── vendor_raw_feed.xlsx       # WF003
│   ├── orders.json                # WF005
│   ├── catalog.csv                # WF006
│   ├── keywords.csv               # WF008
│   ├── employees.json             # WF009
│   └── execution_logs.csv         # WF010
└── tests/
    └── test_all_workflows.py      # Parameterized tests for all 10 workflows
```

## Setup

```bash
cd ai_agent_workflows
pip install -r requirements.txt
```

For LLM-powered workflows (WF004, WF007, WF008), set your API key:

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

Without an API key, the system automatically falls back to mock LLM responses.

## Usage

### Automated Test Mode

Runs all 10 test questions from the Excel `Test_Questions` sheet:

```bash
python main.py --mode test
```

### Interactive CLI Mode

Accepts arbitrary natural-language prompts:

```bash
python main.py
# or
python main.py --mode interactive
```

### Running Tests

```bash
pytest tests/test_all_workflows.py -v -s
```

## Workflows

| ID | Name | Tools | Decision Logic |
|---|---|---|---|
| WF001 | Inventory Restock Check | CSV reader, Calculator | Flag if `current_stock < minimum_stock`; compute reorder qty = `min * 2 - current` |
| WF002 | Product Price Validation | CSV reader, Calculator | Flag if `abs(vendor - internal) / internal * 100 > 10%` |
| WF003 | Vendor File Processing | Excel parser, Validator | Flag rows missing SKU or product name |
| WF004 | Product Description Generator | LLM, Text Validator | Do not invent missing attributes; flag them explicitly |
| WF005 | Customer Order Status | Order lookup, Shipment lookup | If order not found, request a valid identifier |
| WF006 | Duplicate Product Detection | CSV reader, Similarity matcher | Exact SKU = definite; >=85% title similarity = possible |
| WF007 | Marketing Campaign Brief | LLM, Product reader | Halt if campaign goal or dates missing |
| WF008 | SEO Keyword Classification | CSV reader, Classifier | Classify into Informational/Commercial/Transactional/Navigational |
| WF009 | Employee Task Assignment | DB reader, Ranking engine | Match skills → rank by capacity → escalate if none suitable |
| WF010 | Workflow Performance Report | Log reader, Calculator | Flag if failure rate > 10% or latency > threshold |

## Extensibility (WF011)

Adding a new workflow requires zero code changes to the engine:

1. Open `AI_Agent_Workflow_Assessment (1).xlsx`
2. Add a new row to the **Workflows** sheet:
   - `Workflow_ID`: `WF011`
   - `Workflow_Name`: `Customer Churn Risk Analysis`
   - `Trigger`: `User asks about customer churn risk`
   - Fill remaining columns (Steps, Decision_Logic, Tools_Required, etc.)
3. Add mock data file(s) under `data/`
4. Add input resolution in `orchestrator.py:_resolve_inputs()` (WF011 branch)
   - *Note:* The loader and router automatically pick up WF011—no registry changes needed
5. Test: `python main.py --mode test`

## How Dynamic Ingest Works

1. **Loader** reads the Excel `Workflows` sheet on startup. Each row becomes a `WorkflowDefinition` with structured `WorkflowStep` objects. The human-readable `Steps` field (e.g., `"Load inventory → compare stock → calculate reorder"`) is parsed into ordered steps via the `→` separator.

2. **Router** uses keyword overlap + fuzzy string matching (rapidfuzz) to route user queries to the best-matching workflow by its `Trigger` and `Workflow_Name`.

3. **Orchestrator** reads each `WorkflowStep.tools` field and looks up the tool in the `ToolRegistry`. The registry maps tool names to callable functions. No step-specific logic exists in the orchestrator—it executes whatever tools the metadata declares.

4. **Tool Registry** uses a decorator pattern (`@register_tool("csv_reader")`) so tools self-register. New tools can be added by registering a new function without changing the orchestrator.
