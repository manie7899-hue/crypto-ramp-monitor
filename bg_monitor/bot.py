#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram-бот «панель каталога» — rich-эмодзи меню как в топовых ботах:
  /start            → меню разделов (🎁 Гифты, 🔌 Шлюзы, 🏦 Биржи, 👛 Кошельки...)
  Раздел            → список платёжек кнопками с эмодзи
  Платёжка          → карточка + ВСЕ прокладки кликабельными кнопками (с иконками типов)
  Любой текст       → поиск по каталогу
Данные: ../gateway_parser/data.json
"""

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA_PATH = Path(BASE.parent / "gateway_parser" / "data.json")
CFG = json.loads((BASE / "tg_config.json").read_text(encoding="utf-8"))
TOKEN = CFG["token"]
API = f"https://api.telegram.org/bot{TOKEN}"

PAGE_SIZE = 24
PART_PAGE = 36

TYPE_EMOJI = {"кошелёк": "👛", "биржа": "🏦", "NFT": "🖼", "DeFi": "🔁",
              "платёжная система": "💳", "гейминг": "🎮", "метавселенная": "🌐",
              "брокер": "📈", "платёжный процессор": "💸", "шлюз": "🔌",
              "интеграция": "🧩", "мерчанты": "🏪", "сайт": "🌐"}

CATS = [
    ("gift", "🎁 Гифты"),
    ("gateway", "🔌 Шлюзы"),
    ("exchange", "🏦 Биржи"),
    ("wallet", "👛 Кошельки"),
    ("swap", "🔁 Обменники"),
    ("processor", "💳 Процессоры"),
    ("stable", "💵 Стабилкоины"),
    ("defi", "🧩 DeFi"),
    ("nft", "🖼 NFT"),
    ("game", "🎮 Гейминг"),
    ("site", "🌐 Сайты"),
    ("merch", "🏪 Мерчанты"),
    ("integ", "🔗 Интеграции"),
    ("other", "📦 Прочее"),
]


def type_emoji(t):
    return TYPE_EMOJI.get(t, "📦")


def cat_of(g):
    t = (g.get("type") or "").lower()
    if "гифт" in t or "ключи" in t:
        return "gift"
    if "обменник" in t or "swap" in t:
        return "swap"
    if "биржа" in t or "cex" in t or "брокер" in t or "необанк" in t:
        return "exchange"
    if "кошел" in t:
        return "wallet"
    if "процессор" in t or "платёжная система" in t or "платеж" in t:
        return "processor"
    if "стабилкоин" in t or "stablecoin" in t:
        return "stable"
    if "шлюз" in t or "ramp" in t or "on-ramp" in t or "онрамп" in t:
        return "gateway"
    if "defi" in t:
        return "defi"
    if "nft" in t:
        return "nft"
    if "гейминг" in t or "метавселен" in t or "game" in t:
        return "game"
    if "мерчант" in t:
        return "merch"
    if "интеграц" in t:
        return "integ"
    if "сайт" in t:
        return "site"
    return "other"


def api(method, **params):
    data = urllib.parse.urlencode(params).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(API + "/" + method, data=data),
                                    timeout=60) as r:
            return json.loads(r.read())
    except Exception as e:
        print("[api]", method, e)
        return None


def send(chat_id, text, kb=None):
    p = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if kb:
        p["reply_markup"] = json.dumps(kb)
    return api("sendMessage", **p)


def edit(chat_id, msg_id, text, kb=None):
    p = {"chat_id": chat_id, "message_id": msg_id, "text": text,
         "disable_web_page_preview": True}
    if kb:
        p["reply_markup"] = json.dumps(kb)
    return api("editMessageText", **p)


def answer_cb(cb_id):
    api("answerCallbackQuery", callback_query_id=cb_id)


def load_data():
    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ---------------------------------------------------------------- меню
def main_menu(d):
    kb = {"inline_keyboard": []}
    for i in range(0, len(CATS), 2):
        row = []
        for key, label in CATS[i:i + 2]:
            cnt = sum(1 for g in d.values() if cat_of(g) == key)
            if cnt:
                row.append({"text": f"{label} ({cnt})", "callback_data": f"cat:{key}"})
        if row:
            kb["inline_keyboard"].append(row)
    kb["inline_keyboard"].append([
        {"text": f"📂 Все платёжки ({len(d)})", "callback_data": "list:0"},
    ])
    kb["inline_keyboard"].append([
        {"text": "🔍 Поиск", "callback_data": "search"},
        {"text": "❓ Помощь", "callback_data": "help"},
    ])
    return kb


def cat_page(d, key, page=0):
    items = [(dom, g) for dom, g in d.items() if cat_of(g) == key]
    items.sort(key=lambda kv: -len(kv[1].get("partners", [])))
    pages = max(1, -(-len(items) // PAGE_SIZE))
    page = min(max(page, 0), pages - 1)
    chunk = items[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    label = dict(CATS).get(key, "📦 Прочее")
    kb = {"inline_keyboard": []}
    row = []
    for dom, g in chunk:
        row.append({"text": f"{type_emoji(g.get('type',''))} {g.get('name', dom)[:22]}",
                    "callback_data": f"gw:{dom}"})
        if len(row) == 2:
            kb["inline_keyboard"].append(row)
            row = []
    if row:
        kb["inline_keyboard"].append(row)
    nav = []
    if page > 0:
        nav.append({"text": "◀ Назад", "callback_data": f"cat:{key}:{page - 1}"})
    nav.append({"text": f"{page + 1}/{pages}", "callback_data": "noop"})
    if page < pages - 1:
        nav.append({"text": "Ещё ▶", "callback_data": f"cat:{key}:{page + 1}"})
    if pages > 1:
        kb["inline_keyboard"].append(nav)
    kb["inline_keyboard"].append([{"text": "🔙 В меню", "callback_data": "menu"}])
    return f"{label} — {len(items)}:", kb


def gateway_card_text(dom, g):
    k = g.get("kyc", {})
    lines = [
        f"{type_emoji(g.get('type',''))} {g.get('name', dom)}",
        f"📍 {dom}",
        f"🏷 {g.get('type', '—')}",
        f"💸 Комиссии: {g.get('fees', '—')}",
        f"🛂 KYC: {k.get('обязателен', '—')}",
    ]
    if k.get("лимиты"):
        lines.append(f"📊 Лимиты: {k['лимиты']}")
    if g.get("notes"):
        lines.append(f"📌 {re.sub(r'\\s+', ' ', g['notes'])[:300]}")
    lines.append("")
    lines.append(f"🔗 Прокладки — {len(g.get('partners', []))}:")
    return "\n".join(lines)


def kb_url(partners, page, dom, cat):
    total = len(partners)
    pages = max(1, -(-total // PART_PAGE))
    page = min(max(page, 0), pages - 1)
    chunk = partners[page * PART_PAGE:(page + 1) * PART_PAGE]
    kb = {"inline_keyboard": []}
    row = []
    for p in chunk:
        label = ((type_emoji(p.get("type", "")) + " ") + (p.get("name") or "?"))[:34]
        url = p.get("url") or ("https://" + dom)
        if not url.startswith("http"):
            url = "https://" + url
        row.append({"text": label, "url": url})
        if len(row) == 2:
            kb["inline_keyboard"].append(row)
            row = []
    if row:
        kb["inline_keyboard"].append(row)
    if pages > 1:
        nav = []
        if page > 0:
            nav.append({"text": "◀ Назад", "callback_data": f"p:{dom}:{page - 1}:{cat}"})
        nav.append({"text": f"{page + 1}/{pages}", "callback_data": "noop"})
        if page < pages - 1:
            nav.append({"text": "Ещё ▶", "callback_data": f"p:{dom}:{page + 1}:{cat}"})
        kb["inline_keyboard"].append(nav)
    kb["inline_keyboard"].append([
        {"text": "🔙 К разделу", "callback_data": f"cat:{cat}"},
        {"text": "🏠 В меню", "callback_data": "menu"},
    ])
    return kb


HELP_TEXT = (
    "❓ Как пользоваться:\n\n"
    "1️⃣ Выбери раздел: 🎁 гифты, 🔌 шлюзы, 🏦 биржи, 👛 кошельки, 🔁 обменники, "
    "💳 процессоры, 💵 стабилкоины.\n"
    "2️⃣ Выбери платёжку — откроется карточка: комиссии, KYC, лимиты.\n"
    "3️⃣ Жми кнопки прокладок — они ведут на сайты.\n\n"
    "🔍 Или просто напиши слово — найду платёжку или прокладку.\n\n"
    "📊 В каталоге: {n} карточек."
)


def handle_update(upd):
    if "message" in upd:
        msg = upd["message"]
        chat = msg["chat"]["id"]
        text = (msg.get("text") or "").strip()
        d = load_data()
        if text.startswith("/"):
            cmd = text.split()[0].split("@")[0]
            if cmd == "/start":
                send(chat, "🔌 Каталог крипто-платёжек и прокладок\n\n"
                           "Выбери раздел 👇 или напиши слово для поиска.",
                     main_menu(d))
            elif cmd == "/menu":
                send(chat, "🏠 Меню:", main_menu(d))
            elif cmd == "/all":
                send(chat, "📂 Все платёжки (по числу прокладок):", list_page(d, 0))
            elif cmd == "/help":
                send(chat, HELP_TEXT.format(n=len(d)), main_menu(d))
            else:
                send(chat, "🤖 Я понимаю /start, /menu, /all, /help — или просто напиши слово.",
                     main_menu(d))
        elif text:
            hits = search_results(d, text)
            if not hits:
                send(chat, f"🤷 По «{text[:60]}» ничего не нашёл. Попробуй другое слово.", main_menu(d))
                return
            kb = {"inline_keyboard": []}
            row = []
            for dom, g in hits:
                row.append({"text": f"{type_emoji(g.get('type',''))} {(g.get('name') or dom)[:24]}",
                            "callback_data": f"gw:{dom}"})
                if len(row) == 2:
                    kb["inline_keyboard"].append(row)
                    row = []
            if row:
                kb["inline_keyboard"].append(row)
            kb["inline_keyboard"].append([{"text": "🏠 В меню", "callback_data": "menu"}])
            send(chat, f"🔎 Нашёл {len(hits)} по «{text[:60]}»:", kb)
    elif "callback_query" in upd:
        cb = upd["callback_query"]
        data = cb.get("data", "")
        chat = cb["message"]["chat"]["id"]
        msg_id = cb["message"]["message_id"]
        answer_cb(cb["id"])
        d = load_data()
        if data == "menu":
            edit(chat, msg_id, "🏠 Меню — выбери раздел 👇", main_menu(d))
        elif data == "help":
            edit(chat, msg_id, HELP_TEXT.format(n=len(d)), main_menu(d))
        elif data == "search":
            edit(chat, msg_id, "🔍 Напиши слово — найду платёжки и прокладки по нему.", main_menu(d))
        elif data == "noop":
            pass
        elif data.startswith("list:"):
            page = int(data.split(":")[1])
            edit(chat, msg_id, "📂 Все платёжки (по числу прокладок):", list_page(d, page))
        elif data.startswith("cat:"):
            parts = data.split(":")
            key = parts[1]
            page = int(parts[2]) if len(parts) > 2 else 0
            title, kb = cat_page(d, key, page)
            edit(chat, msg_id, title, kb)
        elif data.startswith("gw:"):
            dom = data.split(":", 1)[1]
            g = d.get(dom)
            if not g:
                return
            edit(chat, msg_id, gateway_card_text(dom, g)[:3800],
                 kb_url(g.get("partners", []), 0, dom, cat_of(g)))
        elif data.startswith("p:"):
            _, dom, page, cat = data.split(":")
            g = d.get(dom)
            if not g:
                return
            edit(chat, msg_id, gateway_card_text(dom, g)[:3800],
                 kb_url(g.get("partners", []), int(page), dom, cat))


def list_page(d, page=0):
    items = sorted(d.items(), key=lambda kv: -len(kv[1].get("partners", [])))
    pages = max(1, -(-len(items) // PAGE_SIZE))
    page = min(max(page, 0), pages - 1)
    chunk = items[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    kb = {"inline_keyboard": []}
    row = []
    for dom, g in chunk:
        row.append({"text": f"{type_emoji(g.get('type',''))} {g.get('name', dom)[:20]} ({len(g.get('partners', []))})",
                    "callback_data": f"gw:{dom}"})
        if len(row) == 2:
            kb["inline_keyboard"].append(row)
            row = []
    if row:
        kb["inline_keyboard"].append(row)
    nav = []
    if page > 0:
        nav.append({"text": "◀ Назад", "callback_data": f"list:{page - 1}"})
    nav.append({"text": f"{page + 1}/{pages}", "callback_data": "noop"})
    if page < pages - 1:
        nav.append({"text": "Ещё ▶", "callback_data": f"list:{page + 1}"})
    kb["inline_keyboard"].append(nav)
    kb["inline_keyboard"].append([{"text": "🏠 В меню", "callback_data": "menu"}])
    return kb


def search_results(d, q):
    ql = q.lower()
    hits = []
    for dom, g in d.items():
        hay = " ".join([g.get("name", ""), dom, g.get("type", ""),
                        " ".join(p.get("name", "") for p in g.get("partners", []))]).lower()
        if ql in hay:
            hits.append((dom, g))
    hits.sort(key=lambda kv: -len(kv[1].get("partners", [])))
    return hits[:24]


def main():
    offset = 0
    print("[bot] старт")
    while True:
        r = api("getUpdates", offset=offset, timeout=50)
        if not r or not r.get("ok"):
            time.sleep(3)
            continue
        for upd in r["result"]:
            offset = upd["update_id"] + 1
            try:
                handle_update(upd)
            except Exception as e:
                print("[upd]", e)
        time.sleep(1)


if __name__ == "__main__":
    main()
