from __future__ import annotations
from typing import Any, Callable
from functools import wraps


class ToolRegistry:
    """Central registry for all atomic tools. Tools self-register via the
    @register_tool decorator. The orchestrator looks up tools by name at
    runtime to execute workflow steps dynamically."""

    _registry: dict[str, Callable] = {}
    _descriptions: dict[str, str] = {}

    @classmethod
    def register(cls, name: str, description: str = "") -> Callable:
        def decorator(func: Callable) -> Callable:
            cls._registry[name] = func
            cls._descriptions[name] = description
            @wraps(func)
            def wrapper(**kwargs):
                return func(**kwargs)
            return wrapper
        return decorator

    @classmethod
    def execute(cls, name: str, **kwargs) -> Any:
        tool = cls._registry.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' is not registered.")
        return tool(**kwargs)

    @classmethod
    def is_registered(cls, name: str) -> bool:
        return name in cls._registry

    @classmethod
    def list_registered(cls) -> list[str]:
        return list(cls._registry.keys())

    @classmethod
    def get_description(cls, name: str) -> str:
        return cls._descriptions.get(name, "")
