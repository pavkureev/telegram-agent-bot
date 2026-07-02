from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.agents import AGENTS, normalize_agent
from bot.config import Config, load_config
from bot.documents import SUPPORTED_EXTENSIONS, extract_text
from bot.openai_client import AgentRunner
from bot.store import Store

TELEGRAM_LIMIT = 3900
logger = logging.getLogger(__name__)


class BotApp:
    def __init__(self, config: Config):
        self.config = config
        self.store = Store(config.data_dir / "bot.sqlite3")
        self.runner = AgentRunner(
            api_key=config.openai_api_key,
            model=config.openai_model,
            enable_web_search=config.enable_web_search,
            timeout_seconds=config.openai_timeout_seconds,
            max_output_tokens=config.openai_max_output_tokens,
        )

    def is_allowed(self, update: Update) -> bool:
        if not self.config.allowed_user_ids:
            return True
        user = update.effective_user
        return bool(user and user.id in self.config.allowed_user_ids)

    async def guard(self, update: Update) -> bool:
        if self.is_allowed(update):
            return True
        if update.effective_message:
            await update.effective_message.reply_text("Этот бот приватный.")
        return False

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.guard(update):
            return
        await update.effective_message.reply_text(
            "Готов. Выбери агента командой /agent researcher, /agent product, /agent cpo или /agent editor.\n\n"
            "Можно отправлять документы .txt, .md, .pdf, .docx, .pptx. "
            "Длинные ответы я пришлю Markdown-файлом."
        )

    async def ping(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.guard(update):
            return
        await update.effective_message.reply_text("Я на связи.")

    async def agents(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.guard(update):
            return
        lines = ["Доступные агенты:"]
        for agent in AGENTS.values():
            lines.append(f"/agent {agent.key} - {agent.title}: {agent.description}")
        await update.effective_message.reply_text("\n".join(lines))

    async def set_agent(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.guard(update):
            return
        chat_id = update.effective_chat.id
        requested = normalize_agent(context.args[0] if context.args else None)
        if not requested:
            current = self.store.get_agent(chat_id)
            await update.effective_message.reply_text(
                f"Сейчас выбран: {current}. Например: /agent researcher"
            )
            return
        self.store.set_agent(chat_id, requested)
        agent = AGENTS[requested]
        if len(context.args) > 1:
            await update.effective_message.reply_text(f"Выбран агент: {agent.title}. Беру задачу в работу.")
            await self._run_agent(update, requested, " ".join(context.args[1:]))
            return
        await update.effective_message.reply_text(f"Выбран агент: {agent.title}.")

    async def new(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.guard(update):
            return
        self.store.reset_chat(update.effective_chat.id)
        await update.effective_message.reply_text("Начали заново. Контекст очищен, выбранный агент сохранён.")

    async def show_context(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.guard(update):
            return
        items = self.store.get_context(update.effective_chat.id)
        if not items:
            await update.effective_message.reply_text("Контекста пока нет.")
            return
        titles = "\n".join(f"- {item.title}" for item in items)
        await update.effective_message.reply_text(f"В контексте {len(items)} файл(ов):\n{titles}")

    async def clear_context(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.guard(update):
            return
        self.store.clear_context(update.effective_chat.id)
        await update.effective_message.reply_text("Контекст очищен.")

    async def agent_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.guard(update):
            return
        command = (update.effective_message.text or "").split(maxsplit=1)[0]
        agent_key = normalize_agent(command)
        if not agent_key:
            await update.effective_message.reply_text("Не понял, какого агента выбрать.")
            return

        if not context.args:
            self.store.set_agent(update.effective_chat.id, agent_key)
            await update.effective_message.reply_text(f"Выбран агент: {AGENTS[agent_key].title}.")
            return

        await self._run_agent(update, agent_key, " ".join(context.args))

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.guard(update):
            return
        message = update.effective_message
        document = message.document
        filename = document.file_name or "document"
        ext = Path(filename).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            await message.reply_text(
                "Пока я умею читать только .txt, .md, .pdf, .docx и .pptx."
            )
            return

        await message.chat.send_action(ChatAction.TYPING)
        tg_file = await document.get_file()
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / filename
            await tg_file.download_to_drive(custom_path=str(target))
            try:
                text = extract_text(target)
            except Exception as exc:
                await message.reply_text(f"Не смог прочитать файл: {exc}")
                return

        if not text:
            await message.reply_text("Файл прочитан, но текста в нём не нашлось.")
            return

        self.store.add_context(update.effective_chat.id, filename, text)
        await message.reply_text(f"Добавил в контекст: {filename}.")

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.guard(update):
            return
        message = update.effective_message
        text = message.text or ""
        chat_id = update.effective_chat.id

        agent_key, user_message = self._resolve_agent_for_message(chat_id, text)
        await self._run_agent(update, agent_key, user_message)

    async def _run_agent(self, update: Update, agent_key: str, user_message: str) -> None:
        message = update.effective_message
        chat_id = update.effective_chat.id
        agent = AGENTS[agent_key]
        saved_context = self.store.get_context(chat_id)

        logger.info(
            "Running agent=%s chat_id=%s context_items=%s message_chars=%s",
            agent_key,
            chat_id,
            len(saved_context),
            len(user_message),
        )
        await message.reply_text(f"Принял. Агент: {agent.title}. Думаю над задачей.")
        await message.chat.send_action(ChatAction.TYPING)
        try:
            answer = await self.runner.run(agent, user_message, saved_context)
        except Exception as exc:
            logger.exception("Agent run failed")
            await message.reply_text(f"Не получилось получить ответ от модели: {exc}")
            return

        await self._send_answer(message, agent.key, answer)

    def _resolve_agent_for_message(self, chat_id: int, text: str) -> tuple[str, str]:
        parts = text.strip().split(maxsplit=1)
        if parts:
            maybe_agent = normalize_agent(parts[0])
            if maybe_agent and len(parts) > 1:
                return maybe_agent, parts[1]
        return self.store.get_agent(chat_id), text

    async def _send_answer(self, message, agent_key: str, answer: str) -> None:
        if len(answer) <= TELEGRAM_LIMIT:
            await message.reply_text(answer)
            return

        summary = answer[:1600].rsplit("\n", 1)[0].strip()
        if not summary:
            summary = answer[:1600].strip()
        await message.reply_text(
            f"{summary}\n\nПолный ответ длинный, отправляю файлом."
        )

        safe_agent = "".join(ch for ch in agent_key if ch.isalnum() or ch in {"_", "-"})
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=f"-{safe_agent}.md",
            encoding="utf-8",
            delete=False,
        ) as file:
            file.write(answer)
            path = Path(file.name)
        try:
            with path.open("rb") as document:
                await message.reply_document(document=document, filename=f"{safe_agent}-answer.md")
        finally:
            path.unlink(missing_ok=True)


def build_application() -> Application:
    config = load_config()
    bot = BotApp(config)
    application = Application.builder().token(config.telegram_bot_token).build()
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("ping", bot.ping))
    application.add_handler(CommandHandler("agents", bot.agents))
    application.add_handler(CommandHandler("agent", bot.set_agent))
    application.add_handler(CommandHandler("new", bot.new))
    application.add_handler(CommandHandler("context", bot.show_context))
    application.add_handler(CommandHandler("clear_context", bot.clear_context))
    application.add_handler(CommandHandler(["researcher", "research", "product", "cpo", "editor"], bot.agent_command))
    application.add_handler(MessageHandler(filters.Document.ALL, bot.handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_text))
    return application


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    application = build_application()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
