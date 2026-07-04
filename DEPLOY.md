# Server Deployment

The bot must run continuously somewhere. On a laptop it lives only while the terminal process is running. On a server, run it with Docker Compose and `restart: unless-stopped`.

## Target Server

- Host: `204.168.193.255`
- SSH user: `root`
- SSH command: `ssh root@204.168.193.255`
- Server path: `/var/www/telegram-agent-bot`

No inbound port or domain is required because this MVP uses Telegram polling.

## One-Time Server Setup

SSH into the server:

```bash
ssh root@204.168.193.255
mkdir -p /var/www/telegram-agent-bot
cd /var/www/telegram-agent-bot
```

Create `.env` on the server:

```bash
nano .env
```

Fill it:

```env
TELEGRAM_BOT_TOKEN=...
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5
OPENAI_TIMEOUT_SECONDS=240
OPENAI_MAX_OUTPUT_TOKENS=
CONVERSATION_HISTORY_MESSAGES=12
CONVERSATION_HISTORY_MAX_CHARS=24000
TELEGRAM_ALLOWED_USER_IDS=123456789
BOT_DATA_DIR=.data
ENABLE_WEB_SEARCH=true
```

Keep `.env` only on the server. Do not commit it.

## Manual Deploy From Your Mac

From the local project folder:

```bash
cd /Users/pkureev/Documents/Codex/2026-07-01/new-chat
bash scripts/deploy-server.sh
```

This uploads code to `/var/www/telegram-agent-bot`, rebuilds the container, starts it, and runs `nginx -t`.

## GitHub Actions Deploy

The workflow is in `.github/workflows/deploy.yml`.

Full first-time GitHub setup is in [GITHUB_SETUP.md](GITHUB_SETUP.md).

Add these GitHub repository secrets:

- `DEPLOY_HOST` - `204.168.193.255`
- `DEPLOY_USER` - `root`
- `DEPLOY_PATH` - `/var/www/telegram-agent-bot`
- `DEPLOY_SSH_KEY` - private SSH key that can connect as `root` to `204.168.193.255`.

The workflow deploys after push to `main`.

The server `.env` must already exist before the first GitHub Actions deploy.

After upload the workflow runs:

```bash
docker compose up -d --build
docker compose ps
nginx -t
systemctl reload nginx
```

## Start Or Restart Directly On The Server

```bash
cd /var/www/telegram-agent-bot
docker compose up -d --build
```

Check status:

```bash
docker compose ps
docker compose logs -f telegram-agent-bot
nginx -t
```

In Telegram:

```text
/ping
```

Expected answer:

```text
Я на связи.
```

## Update Later

Use either:

- `bash scripts/deploy-server.sh` from your Mac; or
- push to `main` after GitHub Actions is configured.

To update directly on the server after files are uploaded:

```bash
cd /var/www/telegram-agent-bot
docker compose up -d --build
```

## Stop

```bash
docker compose down
```

## Notes

- The bot stores local context in `./data` on the server.
- Because the bot uses polling, only one copy should run at the same time for the same Telegram bot token.
- Stop the local Mac version before starting the server version.
