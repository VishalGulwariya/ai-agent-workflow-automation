from __future__ import annotations
from typing import Any
import json
import os

from tools.registry import ToolRegistry

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


@ToolRegistry.register("order_lookup", "Looks up an order by order ID or customer email from mock data")
def order_lookup(identifier: str) -> dict[str, Any]:
    orders_path = os.path.join(DATA_DIR, "orders.json")
    with open(orders_path, "r") as f:
        orders = json.load(f)

    if identifier and identifier.startswith("ORD-"):
        order = orders.get(identifier)
        if order:
            return {"found": True, "order_id": identifier, "order_data": order}
        return {"found": False, "searched_id": identifier, "error": f"Order '{identifier}' not found. Please provide a valid order ID or email."}

    for oid, odata in orders.items():
        if odata.get("email") == identifier:
            return {"found": True, "order_id": oid, "order_data": odata}
    return {"found": False, "error": f"No order found for identifier '{identifier}'. Please provide a valid order ID or customer email."}


@ToolRegistry.register("shipment_lookup", "Retrieves shipment and tracking information for an order")
def shipment_lookup(order_data: dict) -> dict[str, Any]:
    if isinstance(order_data, str):
        order_data = json.loads(order_data)
    if not order_data:
        return {"tracking_number": None, "status": "No shipment information available"}
    tracking = order_data.get("tracking")
    carrier = order_data.get("carrier", "Unknown")
    status = order_data.get("status", "Unknown")
    if tracking:
        return {
            "tracking_number": tracking,
            "carrier": carrier,
            "status": status,
            "delivered": status.lower() == "delivered"
        }
    return {"tracking_number": None, "carrier": carrier, "status": status, "message": "No tracking information available for this order."}


@ToolRegistry.register("employee_matcher", "Ranks employees by skills and capacity to assign a task")
def employee_matcher(task_requirements: list[str], employees: list[dict], required_skills: list[str] | None = None) -> dict[str, Any]:
    if isinstance(employees, str):
        employees = json.loads(employees)

    skills_to_match = required_skills or task_requirements

    candidates = []
    for emp in employees:
        emp_skills = emp.get("skills", [])
        matched_skills = [s for s in skills_to_match if s in emp_skills]
        if not matched_skills and skills_to_match:
            continue
        available_capacity = emp.get("capacity", 0) - emp.get("active_tasks", 0)
        score = len(matched_skills) * 10 + max(0, available_capacity)
        candidates.append({
            "employee_id": emp.get("id"),
            "name": emp.get("name"),
            "matched_skills": matched_skills,
            "available_capacity": available_capacity,
            "active_tasks": emp.get("active_tasks"),
            "max_capacity": emp.get("capacity"),
            "score": score,
            "escalate": available_capacity <= 0
        })

    candidates.sort(key=lambda c: c["score"], reverse=True)

    if not candidates:
        return {"assigned": False, "escalated": True, "reason": "No employee with required skills found. Escalating to human manager."}

    top = candidates[0]
    if top["available_capacity"] <= 0 and top["escalate"]:
        return {"assigned": False, "escalated": True, "reason": f"Top candidate {top['name']} has no available capacity. Escalating to human manager.", "candidates": candidates}

    return {"assigned": True, "escalated": False, "selected_employee": top, "all_candidates": candidates}
