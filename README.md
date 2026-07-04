# Telegram Agent Bot

Personal Telegram bot that routes requests to several specialized OpenAI agents:

- `researcher` - studies provided documents, searches the web when useful, maps markets, competitors, technologies, methods, and adoption patterns.
- `product` - turns inputs into product hypotheses, CJM, flows, opportunity maps, and experiments.
- `cpo` - reviews materials critically, finds gaps, pressure-tests quality, and suggests stronger directions.
- `editor` - reviews text, interfaces, and presentations from the user's perspective and from the target-action perspective.

Telegram is used as a compact control surface: short summary in chat, long answer as a Markdown file.

## Quick Start

1. Create a Telegram bot with BotFather and copy its token.
2. Create `.env` from `.env.example`.
3. Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. Run:

```bash
python -m bot.main
```

For the always-online server setup at `204.168.193.255`, use [DEPLOY.md](DEPLOY.md).

## Commands

- `/start` - show help.
- `/agents` - show available agents.
- `/agent researcher` - switch the current chat to an agent.
- `/new` - start a fresh thread for the current chat.
- `/context` - show attached context count.
- `/clear_context` - remove attached documents and notes.
- `/memory` - show how many messages are stored for the current chat.
- `/clear_memory` - clear conversation memory without removing attached documents.

You can also prefix a message with an agent name:

```text
/researcher compare AI meeting note tools
/product make hypotheses from this research
/cpo critique this strategy
/editor improve this onboarding copy
```

## Documents

Send `.txt`, `.md`, `.pdf`, `.docx`, or `.pptx` files to the bot. Extracted text is stored as context for the current Telegram chat until `/clear_context` or `/new`.

## Memory

The bot stores recent conversation messages per Telegram chat, so follow-up questions can refer to previous answers. `/new` clears both documents and memory. `/clear_memory` clears only the dialogue history.

Tune memory with:

```env
CONVERSATION_HISTORY_MESSAGES=12
CONVERSATION_HISTORY_MAX_CHARS=24000
```

## Output Style

The bot sends:

1. A short Telegram summary.
2. A full Markdown file when the response is long or structured.

For heavier analytical tasks, increase `OPENAI_TIMEOUT_SECONDS` in `.env`.

## Security Notes

This is intentionally scoped to analysis agents. It does not execute shell commands, modify repositories, or access your filesystem outside the documents you send to the bot.

Set `TELEGRAM_ALLOWED_USER_IDS` to your Telegram numeric user ID to keep the bot private.
