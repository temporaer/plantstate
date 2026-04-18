"""LLM interpret endpoint — added to API routes."""

from __future__ import annotations

from pydantic import BaseModel


class InterpretRequest(BaseModel):
    """Request body for plant interpretation."""

    user_input: str
    provider: str = "openai"  # extensible later


class InterpretResponse(BaseModel):
    """Response with validated LLM output for preview."""

    name: str
    botanical_name: str | None = None
    description: str = ""
    language: str
    rules: list[dict]
    raw_json: dict
