from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI

from bot.agents import Agent
from bot.store import ContextItem, ConversationMessage


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

    async def run(
        self,
        agent: Agent,
        user_message: str,
        context: list[ContextItem],
        history: list[ConversationMessage],
    ) -> str:
        prompt = self._build_user_prompt(user_message, context, history)
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
        text = self._extract_response_text(response)
        if text:
            return text

        incomplete_reason = getattr(getattr(response, "incomplete_details", None), "reason", None)
        if incomplete_reason == "max_output_tokens":
            return (
                "Ответ не поместился в текущий лимит токенов и был обрезан до того, "
                "как модель успела сформировать финальный текст.\n\n"
                "Что можно сделать:\n"
                "1. Увеличить `OPENAI_MAX_OUTPUT_TOKENS` в `.env`, например до `10000`.\n"
                "2. Попросить более узкий ответ: только список цен, без анализа.\n"
                "3. Разбить задачу на несколько продуктов или подписок."
            )

        return "Модель вернула ответ без текстового содержимого. Попробуй переформулировать запрос короче."

    def _extract_response_text(self, response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if output_text:
            return str(output_text).strip()

        parts: list[str] = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                text = getattr(content, "text", None)
                if text:
                    parts.append(str(text))
        return "\n\n".join(part.strip() for part in parts if part.strip()).strip()

    def _build_user_prompt(
        self,
        user_message: str,
        context: list[ContextItem],
        history: list[ConversationMessage],
    ) -> str:
        context_text = "\n\n".join(
            f"## Document: {item.title}\n{item.content}"
            for item in context
        )
        if not context_text:
            context_text = "No documents or saved context were provided."

        history_text = "\n\n".join(
            f"[{item.role} via {item.agent}]\n{item.content}"
            for item in history
        )
        if not history_text:
            history_text = "No prior conversation history."

        return f"""
# Provided context
{context_text}

# Prior conversation history
{history_text}

# User request
{user_message}
""".strip()
