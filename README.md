# Crypto Ramp Monitor 🔌

Каталог крипто-платёжек, обменников и «прокладок» + фоновый мониторинг новых интеграций.

- 📊 **Панель:** https://manie7899-hue.github.io/crypto-ramp-monitor/
- 🤖 Фоновый мониторинг: каждые 30 минут (GitHub Actions) — новые находки → Telegram-бот
- 🗂 Данные: gateway_parser/data.json (правь вручную, панель пересоберётся)

Структура:
- `gateway_parser/` — каталог (data.json) и генератор панели (build_panel.py)
- `bg_monitor/` — фоновый мониторинг (monitor.py), находки (new_finds.json)
- `.github/workflows/monitor.yml` — расписание и автокоммиты
