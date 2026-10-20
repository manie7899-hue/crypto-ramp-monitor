#!/usr/bin/env bash
# Установщик для VPS (Ubuntu 22.04/24.04): бот + монитор + панель.
# Запуск: bash install.sh <TG_BOT_TOKEN> <TG_CHAT_ID> <GITHUB_PAT>
set -e
TG_BOT_TOKEN="${1:-}"
TG_CHAT_ID="${2:-}"
GITHUB_PAT="${3:-}"
REPO_URL="https://github.com/manie7899-hue/crypto-ramp-monitor.git"
APP_DIR="/opt/crypto-ramp-monitor"

if [ -z "$TG_BOT_TOKEN" ] || [ -z "$TG_CHAT_ID" ] || [ -z "$GITHUB_PAT" ]; then
  echo "Использование: bash install.sh <TG_BOT_TOKEN> <TG_CHAT_ID> <GITHUB_PAT>"; exit 1
fi

echo "[1/6] Ставим пакеты..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y -qq
apt-get install -y -qq git python3 nginx curl >/dev/null

echo "[2/6] Клонируем проект..."
rm -rf "$APP_DIR"
git clone -q "$REPO_URL" "$APP_DIR"

echo "[3/6] Прописываем конфиг бота и git..."
cat > "$APP_DIR/bg_monitor/tg_config.json" <<CFG
{"token": "$TG_BOT_TOKEN", "chat_id": "$TG_CHAT_ID"}
CFG
git -C "$APP_DIR" remote set-url origin "https://x-access-token:${GITHUB_PAT}@github.com/manie7899-hue/crypto-ramp-monitor.git"
git -C "$APP_DIR" config user.name "vps-monitor"
git -C "$APP_DIR" config user.email "vps@users.noreply.github.com"

echo "[4/6] systemd: бот (24/7) + монитор (каждые 30 мин)..."
cat > /etc/systemd/system/crypto-bot.service <<UNIT
[Unit]
Description=Crypto catalog Telegram bot (buttons)
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=$APP_DIR/bg_monitor
ExecStart=/usr/bin/python3 $APP_DIR/bg_monitor/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
UNIT

cat > /etc/systemd/system/crypto-monitor.service <<UNIT
[Unit]
Description=Crypto ramp monitor cycle (search + rebuild + push)
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$APP_DIR
Environment=DATA_JSON=$APP_DIR/gateway_parser/data.json
ExecStart=/bin/bash $APP_DIR/vps_setup/run_cycle.sh

[Install]
WantedBy=multi-user.target
UNIT

cat > /etc/systemd/system/crypto-monitor.timer <<UNIT
[Unit]
Description=Run crypto monitor every 30 minutes

[Timer]
OnCalendar=*:0/30
Persistent=true

[Install]
WantedBy=timers.target
UNIT

echo "[5/6] Панель через nginx..."
cp "$APP_DIR/index.html" /var/www/html/index.html
systemctl enable --now nginx >/dev/null 2>&1 || true

echo "[6/6] Запускаем..."
systemctl daemon-reload
systemctl enable --now crypto-bot.service
systemctl enable --now crypto-monitor.timer
sleep 3
echo ""
echo "=== СТАТУС ==="
systemctl is-active crypto-bot.service && echo "бот: OK"
systemctl list-timers crypto-monitor.timer --no-pager | head -3
IP=$(curl -s -4 ifconfig.me || echo "IP сервера")
echo "Панель: http://$IP/"
echo "Готово."
