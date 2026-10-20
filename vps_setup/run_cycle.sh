#!/usr/bin/env bash
# Цикл мониторинга: поиск новых сайтов -> пересборка панели -> коммит/пуш
set -e
cd "$(dirname "$0")/.."
export DATA_JSON="/opt/crypto-ramp-monitor/gateway_parser/data.json"
python3 bg_monitor/monitor.py >> /var/log/crypto-monitor.log 2>&1 || true
python3 gateway_parser/build_panel.py >> /var/log/crypto-monitor.log 2>&1 || true
cp gateway_parser/panel.html index.html
git add -A
if git diff --cached --quiet; then
  echo "[$(date -u +'%F %T')] изменений нет" >> /var/log/crypto-monitor.log
else
  git commit -qm "auto(vps): обновление каталога $(date -u +'%F %T')"
  git push -q origin main
  echo "[$(date -u +'%F %T')] запушено" >> /var/log/crypto-monitor.log
fi
