# GitHub Deployment Setup

This project deploys through GitHub Actions on every push to `main`.

## 1. Create The GitHub Repo

Recommended repository:

```text
git@github.com:pavkureev/telegram-agent-bot.git
```

Create it in GitHub as an empty repository.

## 2. Add GitHub Secrets

In the new repository:

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

Add:

```text
DEPLOY_HOST=204.168.193.255
DEPLOY_USER=root
DEPLOY_PATH=/var/www/telegram-agent-bot
DEPLOY_SSH_KEY=<private ssh key>
```

Do not paste the private key into chat.

The matching public key must be present on the server:

```bash
/root/.ssh/authorized_keys
```

## 3. Prepare Server Env

On the server:

```bash
ssh root@204.168.193.255
mkdir -p /var/www/telegram-agent-bot
cd /var/www/telegram-agent-bot
nano .env
```

Use:

```env
TELEGRAM_BOT_TOKEN=...
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5
OPENAI_TIMEOUT_SECONDS=240
OPENAI_MAX_OUTPUT_TOKENS=6000
TELEGRAM_ALLOWED_USER_IDS=...
BOT_DATA_DIR=.data
ENABLE_WEB_SEARCH=true
```

## 4. Initialize Local Git And Push

From this local project folder:

```bash
cd /Users/pkureev/Documents/Codex/2026-07-01/new-chat
git init -b main
git remote add origin git@github.com:pavkureev/telegram-agent-bot.git
git status
git add .
git commit -m "Initial telegram agent bot"
git push -u origin main
```

The `.env`, `.venv`, `.data`, `data`, `work`, and `outputs` folders are ignored.

## 5. Check Deploy

After push:

```text
GitHub -> pavkureev/telegram-agent-bot -> Actions
```

The workflow should:

1. checkout repo;
2. connect to `DEPLOY_HOST`;
3. upload files to `DEPLOY_PATH`;
4. run Docker Compose;
5. run `nginx -t`;
6. run `systemctl reload nginx`.

## 6. Verify Bot

In Telegram:

```text
/ping
```

Expected:

```text
Я на связи.
```
