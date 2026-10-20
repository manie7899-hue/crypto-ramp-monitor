# Установка на VPS (404 Core, Германия, Ubuntu)

1. Купи сервер 404 Core (Германия), выбери ОС **Ubuntu 24.04**.
2. Зайди по SSH (пароль/ключ от хоста):
   ```bash
   ssh root@IP_СЕРВЕРА
   ```
3. Выполни одну команду (подставь свои значения):
   ```bash
   curl -fsSL https://raw.githubusercontent.com/manie7899-hue/crypto-ramp-monitor/main/vps_setup/install.sh | bash -s -- "ТОКЕН_БОТА" "CHAT_ID" "GITHUB_PAT"
   ```
   - ТОКЕН_БОТА — от @BotFather
   - CHAT_ID — от @userinfobot
   - GITHUB_PAT — классический токен GitHub (repo + workflow)
4. Готово:
   - Бот с кнопками — работает 24/7 (systemd, авто-рестарт)
   - Мониторинг — каждые 30 минут (systemd timer), находки → в бота и в каталог
   - Панель — на IP сервера через nginx: `http://IP/`
   - GitHub Pages продолжает обновляться автоматически (монитор коммитит и пушит)

Полезное:
```bash
systemctl status crypto-bot        # статус бота
journalctl -u crypto-bot -f        # логи бота
tail -f /var/log/crypto-monitor.log # логи монитора
```
