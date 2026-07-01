#!/usr/bin/env bash
# One-shot installer for aiogram-music-bot on a fresh Debian/Ubuntu server.
# Installs Docker (if missing), clones the repo, writes .env and starts the bot.
#
# Usage (on the server, as root):
#   BOT_TOKEN=123:abc [PROXY_URL=socks5://user:pass@host:port] bash install.sh
set -euo pipefail

: "${BOT_TOKEN:?Set BOT_TOKEN=... (get it from @BotFather)}"
APP=/opt/aiogram-music-bot
REPO=https://github.com/suffer1aSEO/aiogram-music-bot.git

echo "==> Installing Docker (if needed)…"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi

echo "==> Fetching the code…"
if [ -d "$APP/.git" ]; then
  git -C "$APP" fetch --depth 1 origin master && git -C "$APP" reset --hard origin/master
else
  git clone --depth 1 "$REPO" "$APP"
fi
cd "$APP"

echo "==> Writing .env…"
{
  echo "BOT_TOKEN=${BOT_TOKEN}"
  [ -n "${PROXY_URL:-}" ] && echo "PROXY_URL=${PROXY_URL}"
} > .env

echo "==> Building & starting the container…"
docker compose up -d --build

echo "==> Recent logs:"
sleep 4
docker compose logs --tail=25 || true

echo "==> Done. Manage it with:"
echo "    cd $APP && docker compose logs -f      # live logs"
echo "    cd $APP && docker compose restart      # restart"
echo "    cd $APP && docker compose down         # stop"
