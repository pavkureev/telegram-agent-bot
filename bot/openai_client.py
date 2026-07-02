from __future__ import annotations

from openai import AsyncOpenAI

from bot.agents import Agent
from bot.store import ContextItem


class AgentRunner:
    def __init__(
        self,
        api_key: str,
        model: str,
        enable_web_search: bool,
        timeout_seconds: float,
        max_output_tokens: int | None,
    ):
        self.client = AsyncOpenAI(
            api_key=api_key,
            timeout=timeout_seconds,
            max_retries=1,
        )
        self.model = model
        self.enable_web_search = enable_web_search
        self.max_output_tokens = max_output_tokens

    async def run(self, agent: Agent, user_message: str, context: list[ContextItem]) -> str:
        prompt = self._build_user_prompt(user_message, context)
        kwargs = {
            "model": self.model,
            "instructions": agent.system_prompt,
            "input": prompt,
        }
        if self.max_output_tokens:
            kwargs["max_output_tokens"] = self.max_output_tokens

        if agent.allow_web_search and self.enable_web_search:
            kwargs["tools"] = [{"type": "web_search_preview"}]

        response = await self.client.responses.create(**kwargs)
        text = getattr(response, "output_text", None)
        if text:
            return str(text).strip()
        return str(response).strip()

    def _build_user_prompt(self, user_message: str, context: list[ContextItem]) -> str:
        context_text = "\n\n".join(
            f"## Document: {item.title}\n{item.content}"
            for item in context
        )
        if not context_text:
            context_text = "No documents or saved context were provided."

        return f"""
# Provided context
{context_text}

# User request
{user_message}
""".strip()
