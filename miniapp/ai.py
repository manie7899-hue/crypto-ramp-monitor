#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI-чат для Mini App: OpenAI-совместимый эндпоинт + действия по каталогу."""
import json
import re
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
CFG_PATH = BASE / "ai_config.json"
DEFAULT = {"base_url": "https://text.pollinations.ai/openai", "model": "openai", "api_key": ""}


def cfg():
    try:
        c = json.loads(CFG_PATH.read_text(encoding="utf-8"))
        return {**DEFAULT, **c}
    except Exception:
        return dict(DEFAULT)


SYSTEM = """Ты — ассистент каталога крипто-платёжек и их «прокладок» (сайтов, где встроен шлюз).
Ты умеешь и отвечать на вопросы, и ВЫПОЛНЯТЬ действия.

Если пользователь просит действие — верни РОВНО ОДИН JSON-объект без пояснений:
{"action":"add","domain":"site.com","name":"Название"}            — добавить сайт в каталог
{"action":"hunt","topic":"gift card marketplace"}                  — запустить охотника (поиск новых сайтов в вебе)
{"action":"search","query":"wert"}                                 — поиск по каталогу
{"action":"stats"}                                                 — статистика каталога
{"action":"list","category":"gift|exchange|wallet|gateway|swap|processor|defi"} — список раздела
{"action":"answer","text":"..."}                                   — просто ответ

Если это обычный вопрос — отвечай нормальным текстом (без JSON), кратко и по делу, на русском.
Каталог: крипто-шлюзы (MoonPay, Wert, Paybis, Transak…), гифт-карты (Kinguin, Eneba…), биржи, кошельки.
"""


def complete(messages, timeout=70):
    c = cfg()
    body = {"model": c.get("model") or "openai", "messages": messages}
    headers = {"Content-Type": "application/json"}
    if c.get("api_key"):
        headers["Authorization"] = "Bearer " + c["api_key"]
    req = urllib.request.Request(c["base_url"], data=json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8", "ignore"))
    msg = data["choices"][0]["message"]
    return (msg.get("content") or "").strip()


def parse_action(text):
    m = re.search(r"\{[^{}]*\"action\"[^{}]*\}", text, re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if obj.get("action") else None
    except Exception:
        return None
