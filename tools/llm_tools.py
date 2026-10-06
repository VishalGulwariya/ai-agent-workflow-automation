from __future__ import annotations
from typing import Any
import os

from tools.registry import ToolRegistry

try:
    from openai import OpenAI
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False

import json


@ToolRegistry.register("llm_content_generator", "Generates LLM-driven content with hallucination prevention")
def llm_content_generator(prompt: str, product_attributes: dict | None = None, guardrails: list[str] | None = None, model: str = "gpt-4o-mini") -> dict[str, Any]:
    if isinstance(product_attributes, str):
        product_attributes = json.loads(product_attributes)

    missing_fields = []
    if product_attributes:
        for field_name in ["material", "color", "audience", "category"]:
            if not product_attributes.get(field_name):
                missing_fields.append(field_name)

    if not _HAS_OPENAI or not os.getenv("OPENAI_API_KEY"):
        return _generate_mock_content(prompt, product_attributes, missing_fields, guardrails)

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    full_prompt = f"{prompt}\n"
    if product_attributes:
        full_prompt += f"\nProduct attributes: {json.dumps(product_attributes)}\n"
    if guardrails:
        full_prompt += f"\nGuardrails: {' '.join(guardrails)}\n"
    if missing_fields:
        full_prompt += f"\nNOTE: The following fields are MISSING: {missing_fields}. Explicitly flag them as missing. Do not invent data.\n"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful content assistant. Follow all guardrails strictly."},
            {"role": "user", "content": full_prompt}
        ],
        max_tokens=500
    )
    content = response.choices[0].message.content

    return {
        "generated_content": content,
        "missing_fields": missing_fields,
        "guardrails_applied": guardrails,
        "model_used": model
    }


def _generate_mock_content(prompt: str, attributes: dict | None, missing_fields: list, guardrails: list | None) -> dict[str, Any]:
    product_name = attributes.get("name", "Unknown Product") if attributes else "Unknown Product"
    content = _mock_response(prompt, product_name, missing_fields, guardrails)
    return {
        "generated_content": content,
        "missing_fields": missing_fields,
        "guardrails_applied": guardrails,
        "model_used": "mock-gpt-4o-mini"
    }


def _mock_response(prompt: str, name: str, missing_fields: list, guardrails: list | None) -> dict[str, Any]:
    ptype = "description"
    if "seo title" in prompt.lower():
        ptype = "seo_title"
    elif "meta" in prompt.lower():
        ptype = "meta_description"
    elif "campaign" in prompt.lower():
        ptype = "campaign_brief"
    elif "classify" in prompt.lower():
        ptype = "classification"
    elif "keyword" in prompt.lower():
        ptype = "classification"

    result = {}
    if ptype == "description":
        result = {
            "short_description": f"A premium {name} designed for comfort and reliability.",
            "long_description": f"The {name} offers exceptional quality and performance for everyday use.",
            "missing_fields": missing_fields
        }
    elif ptype == "seo_title":
        result = {"seo_title": f"Buy {name} | Premium Quality | Fast Shipping"}
    elif ptype == "meta_description":
        result = {"meta_description": f"Shop {name} at the best price. High-quality, fast delivery, and excellent customer service. Order now!"}
    elif ptype == "campaign_brief":
        result = {
            "objective": "Increase awareness and drive sales for the new collection.",
            "target_audience": "Democratized marketing - all demographics",
            "messaging": "Experience quality redefined with our new collection.",
            "channels": ["Email", "Social Media", "Paid Search"],
            "timeline": "2026-10-01 to 2026-10-31",
            "checklist": ["Define KPIs", "Create creatives", "Launch ads"]
        }
    elif ptype == "classification":
        result = {"classified": prompt}
    else:
        result = {"content": f"{prompt}\n(missing: {missing_fields})"}
    return result


@ToolRegistry.register("llm_text_generator", "Generates text content using LLM or mock mode")
def llm_text_generator(prompt: str, context: dict | None = None, output_format: str = "text") -> dict[str, Any]:
    if _HAS_OPENAI and os.getenv("OPENAI_API_KEY"):
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        full_prompt = f"{prompt}\n"
        if context:
            full_prompt += f"\nContext: {json.dumps(context, indent=2)}\n"
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": full_prompt}
            ],
            max_tokens=500
        )
        return {"generated_content": response.choices[0].message.content.strip(), "model_used": "gpt-4o-mini"}

    mock = _mock_text(prompt, context)
    return {"generated_content": mock, "model_used": "mock-gpt-4o-mini"}


def _mock_text(prompt: str, context: dict | None) -> str:
    if "campaign brief" in prompt.lower():
        return (
            "Campaign Brief: New Collection Launch\n"
            "Objective: Build awareness for the new collection.\n"
            "Target Audience: Fashion-forward consumers aged 18-35.\n"
            "Messaging: Innovation meets style in every piece.\n"
            "Channels: Social Media, Paid Search, Email Marketing.\n"
            "Timeline: October 1 - October 31, 2026.\n"
            "Checklist: Define KPIs, design creatives, schedule posts, launch ads."
        )
    if "seo content" in prompt.lower():
        return (
            "Short Description: A sleek, modern design for everyday elegance.\n"
            "Long Description: This product combines premium materials with contemporary aesthetics.\n"
            "SEO Title: Premium Product | Stylish Design | Fast Delivery\n"
            "Meta Description: Discover premium quality with modern design. Shop now for fast delivery!"
        )
    return f"Generated response to: {prompt[:80]}..."
