#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram-бот «панель каталога» — интерактивные кнопки:
  /start           → главное меню с топ-платёжками
  Кнопка платёжки  → карточка (комиссии, KYC) + ВСЕ прокладки кликабельными кнопками
  Любой текст      → поиск по каталогу (имя/домен/прокладки)
Работает на чистом stdlib (long-polling). Данные: ../gateway_parser/data.json
"""

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA_PATH = Path(BASE.parent / "gateway_parser" / "data.json")
CFG = json.loads((BASE / "tg_config.json").read_text(encoding="utf-8"))
TOKEN = CFG["token"]
API = f"https://api.telegram.org/bot{TOKEN}"

TOP_DOMAINS = ["paybis.com", "moonpay.com", "transak.com", "ramp.network", "mercuryo.io",
               "banxa.com", "wert.io", "topperpay.com", "onramper.com", "changelly.com",
               "simplex.com", "alchemypay.org", "swipelux.com", "utorg.io", "guardarian.com"]

PAGE_SIZE = 24   # платёжек на страницу списка
PART_PAGE = 36   # прокладок на страницу карточки


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


TYPE_EMOJI = {"кошелёк":"👛","биржа":"🏦","NFT":"🖼","DeFi":"🔁","платёжная система":"💳",
              "гейминг":"🎮","метавселенная":"🌐","брокер":"📈","платёжный процессор":"💸",
              "шлюз":"🔌","интеграция":"🧩","мерчанты":"🏪","сайт":"🌐"}

def type_emoji(t):
    return TYPE_EMOJI.get(t, "📦")

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
        notes = re.sub(r"\s+", " ", g["notes"])
        lines.append(f"📌 {notes[:300]}")
    parts = g.get("partners", [])
    lines.append("")
    lines.append(f"🔗 Прокладки — {len(parts)}:")
    return "\n".join(lines)


def kb_url(partners, page, dom):
    """Клавиатура из URL-кнопок прокладок + пагинация + назад."""
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
            nav.append({"text": "◀", "callback_data": f"p:{dom}:{page - 1}"})
        nav.append({"text": f"{page + 1}/{pages}", "callback_data": "noop"})
        if page < pages - 1:
            nav.append({"text": "▶", "callback_data": f"p:{dom}:{page + 1}"})
        kb["inline_keyboard"].append(nav)
    kb["inline_keyboard"].append([{"text": "🔙 К меню", "callback_data": "menu"},
                                  {"text": "🔍 Поиск", "callback_data": "search"}])
    return kb


def main_menu():
    d = load_data()
    kb = {"inline_keyboard": []}
    row = []
    for dom in TOP_DOMAINS:
        g = d.get(dom)
        name = (g or {}).get("name", dom)
        label = name[:28]
        row.append({"text": label, "callback_data": f"gw:{dom}"})
        if len(row) == 2:
            kb["inline_keyboard"].append(row)
            row = []
    if row:
        kb["inline_keyboard"].append(row)
    kb["inline_keyboard"].append([
        {"text": f"📂 Все платёжки ({len(d)})", "callback_data": "list:0"},
    ])
    kb["inline_keyboard"].append([
        {"text": "🎁 Гифты", "callback_data": "list:gift"},
    ])
    kb["inline_keyboard"].append([
        {"text": "🔍 Поиск — напиши слово", "callback_data": "search"},
    ])
    return kb


def list_page(page):
    d = load_data()
    items = sorted(d.items(), key=lambda kv: -len(kv[1].get("partners", [])))
    pages = max(1, -(-len(items) // PAGE_SIZE))
    page = min(max(page, 0), pages - 1)
    chunk = items[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    kb = {"inline_keyboard": []}
    row = []
    for dom, g in chunk:
        label = f"{(g.get('name') or dom)[:24]} ({len(g.get('partners', []))})"
        row.append({"text": label, "callback_data": f"gw:{dom}"})
        if len(row) == 2:
            kb["inline_keyboard"].append(row)
            row = []
    if row:
        kb["inline_keyboard"].append(row)
    nav = []
    if page > 0:
        nav.append({"text": "◀", "callback_data": f"list:{page - 1}"})
    nav.append({"text": f"{page + 1}/{pages}", "callback_data": "noop"})
    if page < pages - 1:
        nav.append({"text": "▶", "callback_data": f"list:{page + 1}"})
    kb["inline_keyboard"].append(nav)
    kb["inline_keyboard"].append([{"text": "🔙 К меню", "callback_data": "menu"}])
    return kb


def search_results(q):
    d = load_data()
    ql = q.lower()
    hits = []
    for dom, g in d.items():
        hay = " ".join([g.get("name", ""), dom, g.get("type", ""),
                        " ".join(p.get("name", "") for p in g.get("partners", []))]).lower()
        if ql in hay:
            hits.append((dom, g))
    hits.sort(key=lambda kv: -len(kv[1].get("partners", [])))
    return hits[:24]


def handle_update(upd):
    if "message" in upd:
        msg = upd["message"]
        chat = msg["chat"]["id"]
        text = (msg.get("text") or "").strip()
        if text.startswith("/"):
            cmd = text.split()[0].split("@")[0]
            if cmd == "/start":
                send(chat,
                     "🔌 Каталог крипто-платёжек и прокладок.\n\n"
                     "Жми на платёжку — покажу ВСЕ её прокладки кликабельными кнопками.\n"
                     "Или просто напиши слово для поиска (например: paybis, metamask, wert).",
                     main_menu())
            elif cmd == "/menu":
                send(chat, "Меню:", main_menu())
            elif cmd == "/all":
                send(chat, "Все платёжки (по числу прокладок):", list_page(0))
            elif cmd == "/search":
                send(chat, "Напиши слово — найду платёжки и прокладки по нему.", main_menu())
        elif text:
            hits = search_results(text)
            if not hits:
                send(chat, f"🤷 По «{text[:60]}» ничего не нашёл. Попробуй другое слово.", main_menu())
                return
            kb = {"inline_keyboard": []}
            row = []
            for dom, g in hits:
                label = f"{(g.get('name') or dom)[:26]} ({len(g.get('partners', []))})"
                row.append({"text": label, "callback_data": f"gw:{dom}"})
                if len(row) == 2:
                    kb["inline_keyboard"].append(row)
                    row = []
            if row:
                kb["inline_keyboard"].append(row)
            kb["inline_keyboard"].append([{"text": "🔙 К меню", "callback_data": "menu"}])
            send(chat, f"🔎 Нашёл {len(hits)} по «{text[:60]}»:", kb)
    elif "callback_query" in upd:
        cb = upd["callback_query"]
        data = cb.get("data", "")
        chat = cb["message"]["chat"]["id"]
        msg_id = cb["message"]["message_id"]
        answer_cb(cb["id"])
        d = load_data()
        if data == "menu":
            edit(chat, msg_id, "🔌 Меню — жми на платёжку или напиши слово для поиска:", main_menu())
        elif data == "search":
            edit(chat, msg_id, "🔍 Напиши слово — найду платёжки и прокладки по нему.", main_menu())
        elif data == "noop":
            pass
        elif data == "list:gift":
            items = [(dom, g) for dom, g in d.items() if "гифт" in (g.get("type","").lower())]
            items.sort(key=lambda kv: -len(kv[1].get("partners", [])))
            kb = {"inline_keyboard": []}
            row = []
            for dom, g in items[:48]:
                row.append({"text": f"🎁 {g.get('name', dom)[:24]}", "callback_data": f"gw:{dom}"})
                if len(row) == 2:
                    kb["inline_keyboard"].append(row); row = []
            if row: kb["inline_keyboard"].append(row)
            kb["inline_keyboard"].append([{"text": "🔙 К меню", "callback_data": "menu"}])
            edit(chat, msg_id, f"🎁 Гифт-маркетплейсы ({len(items)}):", kb)
        elif data.startswith("list:"):
            page = int(data.split(":")[1])
            edit(chat, msg_id, "Все платёжки (по числу прокладок):", list_page(page))
        elif data.startswith("gw:"):
            dom = data.split(":", 1)[1]
            g = d.get(dom)
            if not g:
                return
            text = gateway_card_text(dom, g)
            edit(chat, msg_id, text[:3800], kb_url(g.get("partners", []), 0, dom))
        elif data.startswith("p:"):
            _, dom, page = data.split(":")
            g = d.get(dom)
            if not g:
                return
            edit(chat, msg_id, gateway_card_text(dom, g)[:3800],
                 kb_url(g.get("partners", []), int(page), dom))


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
