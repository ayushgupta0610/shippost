"""LLM access for shiplog."""

from shiplog.llm.chat import LLMResult, TokenUsage, chat_structured
from shiplog.llm.client import get_client

__all__ = ["LLMResult", "TokenUsage", "chat_structured", "get_client"]
