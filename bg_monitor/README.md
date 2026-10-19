# 🤖 Фоновый мониторинг крипто-платёжек + Telegram-бот + бесплатный хост

Каждые 30 минут на бесплатном хостинге (GitHub Actions) запускается `bg_monitor/monitor.py`:

1. Ищет новые сайты через Bing / DuckDuckGo / Mojeek — включая запросы по **x.com (твиттер)**, **reddit**, **bitcointalk**.
2. Парсит RSS крипто-СМИ (Cointelegraph, Decrypt, The Block, Bitcoin Magazine) на анонсы партнёрств/интеграций.
3. Проверяет новые домены (живость, заголовок, релевантность теме).
4. Новые находки:
   - автоматически добавляются в `gateway_parser/data.json` (с пометкой «авто-находка»),
   - пишутся в `bg_monitor/new_finds.json`,
   - **прилетают уведомлением в Telegram-бота**.

Панель автоматически пересобирается и публикуется через **GitHub Pages** — постоянная публичная ссылка.

## Как поднять за 10 минут

### 1. Создай Telegram-бота
- В Telegram напиши `@BotFather` → `/newbot` → имя и username бота → получишь **токен** вида `123456:ABC...`.
- Напиши своему боту любое сообщение, затем `@userinfobot` → он покажет твой **chat_id** (цифры).

### 2. Создай репозиторий на GitHub
- Зарегистрируйся на github.com (бесплатно).
- Создай **публичный** репозиторий (публичный = бесплатные минуты Actions без лимита), например `crypto-ramp-monitor`.
- Залей туда папки `gateway_parser/`, `bg_monitor/` и файл `.github/workflows/monitor.yml`:
  ```bash
  # из папки проекта:
  git init
  git add gateway_parser bg_monitor .github
  git commit -m "init"
  git branch -M main
  git remote add origin https://github.com/ТВОЙ_ЛОГИН/crypto-ramp-monitor.git
  git push -u origin main
  ```

### 3. Добавь секреты (токен бота)
- В репозитории: **Settings → Secrets and variables → Actions → New repository secret**:
  - `TG_BOT_TOKEN` = токен бота
  - `TG_CHAT_ID` = твой chat_id

### 4. Включи GitHub Pages
- **Settings → Pages → Source: Deploy from a branch → Branch: main, / (root)** → Save.
- Через минуту панель будет доступна по ссылке:
  `https://ТВОЙ_ЛОГИН.github.io/crypto-ramp-monitor/`

Готово: монитор крутится 24/7 бесплатно, новые находки сыпятся в Telegram, панель обновляется сама.

## Запуск вручную / локально
```bash
python bg_monitor/monitor.py                    # один цикл поиска
TG_BOT_TOKEN=... TG_CHAT_ID=... python bg_monitor/monitor.py   # с уведомлениями
```
