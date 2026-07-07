from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


class RuntimeSkillToolInput(BaseModel):
    query: str
    target_context: dict[str, Any] = Field(default_factory=dict)
    request_context: dict[str, Any] = Field(default_factory=dict)


class RuntimeSkillToolAdapter:
    """Expose one runtime skill as one LangChain tool while hiding procedure internals."""

    def __init__(self, *, name: str, description: str, invoke) -> None:
        self.name = name
        self.description = description
        self.invoke = invoke

    def to_langchain_tool(self):
        return StructuredTool.from_function(
            func=self.invoke,
            name=self.name,
            description=self.description,
            args_schema=RuntimeSkillToolInput,
        )
