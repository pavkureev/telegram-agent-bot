#!/usr/bin/env bash
set -euo pipefail

SERVER="${SERVER:-root@204.168.193.255}"
REMOTE_PATH="${REMOTE_PATH:-/var/www/telegram-agent-bot}"

ssh "$SERVER" "mkdir -p '$REMOTE_PATH'"

rsync -az --delete \
  --exclude ".env" \
  --exclude ".venv" \
  --exclude ".data" \
  --exclude "data" \
  --exclude "work" \
  --exclude "outputs" \
  --exclude "__pycache__" \
  --exclude "*.pyc" \
  ./ "$SERVER:$REMOTE_PATH/"

ssh "$SERVER" "cd '$REMOTE_PATH' && docker compose up -d --build && docker compose ps && nginx -t && systemctl reload nginx"
