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

# ---- премиум (кастомные) эмодзи: emoji -> emoji_id ----
PE_PATH = BASE / "premium_emoji.json"
FAV_PATH = BASE / "favorites.json"


def is_trashed(g):
    return bool(g.get("trashed"))


def trashed_count(d):
    return sum(1 for g in d.values() if is_trashed(g))


def fav_load():
    try:
        return json.loads(FAV_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def fav_save(f):
    FAV_PATH.write_text(json.dumps(f, ensure_ascii=False, indent=1), encoding="utf-8")


def fav_toggle(uid, dom):
    f = fav_load()
    lst = f.setdefault(str(uid), [])
    if dom in lst:
        lst.remove(dom)
        act = "убрал"
    else:
        lst.insert(0, dom)
        act = "добавил"
    fav_save(f)
    return act, lst

APP_URL_PATH = BASE / "miniapp_url.txt"


def app_url():
    try:
        u = APP_URL_PATH.read_text(encoding="utf-8").strip()
        return u if u.startswith("https://") else ""
    except Exception:
        return ""

try:
    PREMIUM = json.loads(PE_PATH.read_text(encoding="utf-8"))
except Exception:
    PREMIUM = {}


def save_premium():
    PE_PATH.write_text(json.dumps(PREMIUM, ensure_ascii=False, indent=1), encoding="utf-8")


def pem(emoji):
    """Оборачивает эмодзи в tg-emoji, если для него сохранён премиум-ID."""
    eid = PREMIUM.get(emoji)
    if eid:
        return f'<tg-emoji emoji-id="{eid}">{emoji}</tg-emoji>'
    return emoji


def utf16_slice(text, offset, length):
    b = text.encode("utf-16-le")
    return b[offset * 2:(offset + length) * 2].decode("utf-16-le", "ignore")

# Bot API 9.4: цвета кнопок (style) и кастомные эмодзи-иконки (icon_custom_emoji_id)
EMOJI_THUMB = "5285430309720966085"
EMOJI_CHECK = "5310076249404621168"
EMOJI_TRASH = "5310169226856644648"
EMOJI_STAR = "5285032475490273112"


def cat_emoji(key):
    return {k: l.split()[0] for k, l, _ in CATS}.get(key, "📦")


def ebtn(emoji, text, cb=None, url=None, style=None):
    """Кнопка: если для эмодзи есть премиум-ID — иконка, иначе эмодзи в тексте."""
    eid = PREMIUM.get(emoji)
    if eid:
        return btn(text, cb=cb, url=url, style=style, icon=eid)
    return btn(f"{emoji} {text}", cb=cb, url=url, style=style)


def btn(text, cb=None, url=None, style=None, icon=None):
    b = {"text": text}
    if cb:
        b["callback_data"] = cb
    if url:
        b["url"] = url
    if style:
        b["style"] = style
    if icon:
        b["icon_custom_emoji_id"] = icon
    return b

TYPE_EMOJI = {"кошелёк": "👛", "биржа": "🏦", "NFT": "🖼", "DeFi": "🔁",
              "платёжная система": "💳", "гейминг": "🎮", "метавселенная": "🌐",
              "брокер": "📈", "платёжный процессор": "💸", "шлюз": "🔌",
              "интеграция": "🧩", "мерчанты": "🏪", "сайт": "🌐"}

CATS = [
    ("gift", "🎁 Гифты", "success"),
    ("gateway", "🔌 Шлюзы", "primary"),
    ("exchange", "🏦 Биржи", "primary"),
    ("wallet", "👛 Кошельки", None),
    ("swap", "🔁 Обменники", "success"),
    ("processor", "💳 Процессоры", None),
    ("stable", "💵 Стабилкоины", "success"),
    ("defi", "🧩 DeFi", "primary"),
    ("nft", "🖼 NFT", None),
    ("game", "🎮 Гейминг", None),
    ("site", "🌐 Сайты", None),
    ("merch", "🏪 Мерчанты", None),
    ("integ", "🔗 Интеграции", None),
    ("other", "📦 Прочее", None),
]


def type_emoji(t):
    if t in TYPE_EMOJI:
        return TYPE_EMOJI[t]
    s = (t or "").lower()
    if "гифт" in s or "ключ" in s:
        return "🎁"
    if "обменник" in s or "swap" in s:
        return "🔁"
    if "биржа" in s or "cex" in s or "брокер" in s:
        return "🏦"
    if "кошел" in s:
        return "👛"
    if "процессор" in s or "платёжная система" in s or "платеж" in s:
        return "💳"
    if "стабилкоин" in s:
        return "💵"
    if "шлюз" in s or "ramp" in s or "онрамп" in s:
        return "🔌"
    if "defi" in s:
        return "🧩"
    if "nft" in s:
        return "🖼"
    if "гейминг" in s or "метавселен" in s:
        return "🎮"
    if "мерчант" in s:
        return "🏪"
    if "интеграц" in s:
        return "🔗"
    if "сайт" in s:
        return "🌐"
    return "📦"


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
    p = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True,
         "parse_mode": "HTML"}
    if kb:
        p["reply_markup"] = json.dumps(kb)
    return api("sendMessage", **p)


def edit(chat_id, msg_id, text, kb=None):
    p = {"chat_id": chat_id, "message_id": msg_id, "text": text,
         "disable_web_page_preview": True, "parse_mode": "HTML"}
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
def main_menu(d, private=False):
    kb = {"inline_keyboard": []}
    for i in range(0, len(CATS), 2):
        row = []
        for key, label, style in CATS[i:i + 2]:
            cnt = sum(1 for g in d.values() if cat_of(g) == key and not is_trashed(g))
            if cnt:
                emoji, title = label.split(" ", 1)
                row.append(ebtn(emoji, f"{title} ({cnt})", cb=f"cat:{key}", style=style))
        if row:
            kb["inline_keyboard"].append(row)
    kb["inline_keyboard"].append([
        ebtn("📂", f"Все платёжки ({sum(1 for g in d.values() if not is_trashed(g))})", cb="list:0", style="primary"),
    ])
    kb["inline_keyboard"].append([
        ebtn("🔍", "Поиск", cb="search", style="primary"),
        ebtn("❓", "Помощь", cb="help"),
    ])
    kb["inline_keyboard"].append([ebtn("⭐", "Избранное", cb="fav:0")])
    tc = trashed_count(d)
    if tc:
        kb["inline_keyboard"].append([ebtn("🗑", f"Корзина ({tc})", cb="trash:0")])
    u = app_url()
    if u:
        if private:
            kb["inline_keyboard"].append([{"text": "🎛 Открыть Mini App", "web_app": {"url": u + "/app/"}}])
        else:
            kb["inline_keyboard"].append([{"text": "🎛 Mini App", "url": u + "/app/"}])
    return kb


def cat_page(d, key, page=0):
    items = [(dom, g) for dom, g in d.items() if cat_of(g) == key and not is_trashed(g)]
    items.sort(key=lambda kv: -len(kv[1].get("partners", [])))
    pages = max(1, -(-len(items) // PAGE_SIZE))
    page = min(max(page, 0), pages - 1)
    chunk = items[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    label = {k: l for k, l, _ in CATS}.get(key, "📦 Прочее")
    kb = {"inline_keyboard": []}
    row = []
    for dom, g in chunk:
        row.append(ebtn(cat_emoji(key), (g.get('name', dom))[:24], cb=f"gw:{dom}"))
        if len(row) == 2:
            kb["inline_keyboard"].append(row)
            row = []
    if row:
        kb["inline_keyboard"].append(row)
    nav = []
    if page > 0:
        nav.append(btn("◀ Назад", cb=f"cat:{key}:{page - 1}", style="primary"))
    nav.append(btn(f"{page + 1}/{pages}", cb="noop"))
    if page < pages - 1:
        nav.append(btn("Ещё ▶", cb=f"cat:{key}:{page + 1}", style="success"))
    if pages > 1:
        kb["inline_keyboard"].append(nav)
    kb["inline_keyboard"].append([btn("🏠 В меню", cb="menu", style="primary")])
    return f"{label} — {len(items)}:", kb


def gateway_card_text(dom, g):
    k = g.get("kyc", {})
    lines = [
        f"{pem(type_emoji(g.get('type','')))} <b>{g.get('name', dom)}</b>",
        f"{pem('📍')} <code>{dom}</code>",
        f"{pem('🏷')} {g.get('type', '—')}",
        f"{pem('💸')} Комиссии: {g.get('fees', '—')}",
        f"{pem('🛂')} KYC: {k.get('обязателен', '—')}",
    ]
    if k.get("лимиты"):
        lines.append(f"{pem('📊')} Лимиты: {k['лимиты']}")
    pg = g.get("pay_groups") or {}
    if pg.get("card"):
        lines.append(f"{pem('💳')} Карты: {', '.join(pg['card'][:7])}")
    if pg.get("wallet"):
        lines.append(f"{pem('👛')} Кошельки: {', '.join(pg['wallet'][:6])}")
    if pg.get("bank"):
        lines.append(f"{pem('🏦')} Банк: {', '.join(pg['bank'][:6])}")
    if pg.get("crypto"):
        lines.append(f"{pem('🪙')} Крипта: {', '.join(pg['crypto'][:6])}")
    if pg.get("local"):
        lines.append(f"{pem('🏪')} Локальные: {', '.join(pg['local'][:6])}")
    if not pg and g.get("pay"):
        lines.append(f"{pem('💳')} Оплата: {', '.join(g['pay'][:8])}")
    gd = g.get("gateways_detected") or []
    if gd:
        lines.append(f"{pem('🔌')} Шлюз (по коду): " + ", ".join(x["name"] for x in gd[:6]))
    elif g.get("providers"):
        lines.append(f"{pem('🔌')} Шлюзы на сайте: {', '.join(g['providers'][:8])}")
    kv = g.get("kyc_vendors") or []
    if kv:
        lines.append(f"{pem('🛂')} Верификация: " + ", ".join(x["name"] for x in kv[:5]))
    elif g.get("kyc_words"):
        lines.append(f"{pem('🛂')} Верификация: " + ", ".join(g["kyc_words"][:3]))
    if g.get("tds"):
        ev = g.get("tds_evidence", "")
        lines.append(f"{pem('🔐')} 3D-Secure: да" + (f" ({ev})" if ev else ""))
    if g.get("regions"):
        lines.append(f"{pem('🌍')} Регионы: {', '.join(g['regions'][:5])}")
    if g.get("licenses"):
        lines.append(f"{pem('🛡')} Лицензии: {', '.join(g['licenses'][:5])}")
    extra = []
    if g.get("fee_note"):
        extra.append(f"комиссия {g['fee_note']}")
    if g.get("kyc_note"):
        extra.append(g["kyc_note"])
    if g.get("api_kind"):
        extra.append(f"API {g['api_kind']}")
    if g.get("sandbox"):
        extra.append("есть sandbox")
    if extra:
        lines.append(f"{pem('🧪')} " + " · ".join(extra))
    if g.get("docs"):
        lines.append(f"{pem('📚')} <a href=\"{g['docs']}\">Документация</a>")
    if g.get("api"):
        lines.append(f"{pem('🧩')} <a href=\"{g['api']}\">API</a>")
    if is_trashed(g):
        t = g.get("trashed") or {}
        lines.append(f"🗑 <b>В корзине</b>: {t.get('reason', '—')}")
    if g.get("notes"):
        lines.append(f"{pem('📌')} <blockquote>{re.sub(r'\\s+', ' ', g['notes'])[:280]}</blockquote>")
    lines.append("")
    lines.append(f"{pem('🔗')} Прокладки — {len(g.get('partners', []))}:")
    return "\n".join(lines)


def kb_url(partners, page, dom, cat, trashed=False):
    total = len(partners)
    pages = max(1, -(-total // PART_PAGE))
    page = min(max(page, 0), pages - 1)
    chunk = partners[page * PART_PAGE:(page + 1) * PART_PAGE]
    kb = {"inline_keyboard": []}
    row = []
    for p in chunk:
        url = p.get("url") or ("https://" + dom)
        if not url.startswith("http"):
            url = "https://" + url
        row.append(ebtn(type_emoji(p.get("type", "")), (p.get("name") or "?")[:32], url=url))
        if len(row) == 2:
            kb["inline_keyboard"].append(row)
            row = []
    if row:
        kb["inline_keyboard"].append(row)
    if pages > 1:
        nav = []
        if page > 0:
            nav.append(btn("◀ Назад", cb=f"p:{dom}:{page - 1}:{cat}", style="primary"))
        nav.append(btn(f"{page + 1}/{pages}", cb="noop"))
        if page < pages - 1:
            nav.append(btn("Ещё ▶", cb=f"p:{dom}:{page + 1}:{cat}", style="success"))
        kb["inline_keyboard"].append(nav)
    if trashed:
        kb["inline_keyboard"].append([btn("♻️ Восстановить", cb=f"trashrestore:{dom}", style="success")])
    else:
        kb["inline_keyboard"].append([
            btn("⭐ В избранное", cb=f"favadd:{dom}"),
            btn("🗑 В корзину", cb=f"trash:{dom}", style="danger"),
        ])
    kb["inline_keyboard"].append([
        btn("🔙 К разделу", cb=f"cat:{cat}"),
        btn("🏠 В меню", cb="menu", style="primary"),
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
        # сбор кастомных (премиум) эмодзи из сообщения
        got = 0
        for ent in (msg.get("entities") or []):
            if ent.get("type") == "custom_emoji" and ent.get("custom_emoji_id"):
                e = utf16_slice(text, ent["offset"], ent["length"])
                if e and e not in PREMIUM:
                    PREMIUM[e] = ent["custom_emoji_id"]
                    got += 1
        if got:
            save_premium()
            send(chat, f"✅ Запомнил {got} премиум-эмодзи (всего {len(PREMIUM)}). "
                       "Теперь они будут в карточках: " + "".join(
                           f'<tg-emoji emoji-id="{v}">{k}</tg-emoji>' for k, v in list(PREMIUM.items())[-got:]),
                 )
        d = load_data()
        if text.startswith("/"):
            cmd = text.split()[0].split("@")[0]
            private = (msg.get("chat", {}).get("type") == "private")
            if cmd == "/start":
                send(chat, "🔌 <b>Каталог крипто-платёжек и прокладок</b>\n\n"
                           "Выбери раздел 👇 или напиши слово для поиска.",
                     main_menu(d, private))
            elif cmd == "/menu":
                send(chat, "🏠 <b>Меню</b>:", main_menu(d))
            elif cmd == "/all":
                send(chat, "📂 Все платёжки (по числу прокладок):", list_page(d, 0))
            elif cmd == "/emoji":
                if PREMIUM:
                    preview = "".join(f'<tg-emoji emoji-id="{v}">{k}</tg-emoji>' for k, v in PREMIUM.items())
                    send(chat, f"🎨 Премиум-эмодзи в базе ({len(PREMIUM)}):\n{preview}\n\n"
                               "Чтобы добавить — просто отправь нужные премиум-эмодзи (можно несколько).")
                else:
                    send(chat, "🎨 Пока пусто. Отправь мне премиум-эмодзи (🎁🔥💎🚀...), "
                               "я запомню их ID и подставлю в карточки.")
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
                row.append(ebtn(type_emoji(g.get('type','')), (g.get('name') or dom)[:24],
                                cb=f"gw:{dom}"))
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
            edit(chat, msg_id, "🏠 <b>Меню</b> — выбери раздел 👇", main_menu(d))
        elif data == "help":
            edit(chat, msg_id, HELP_TEXT.format(n=len(d)), main_menu(d))
        elif data == "search":
            edit(chat, msg_id, "🔍 Напиши слово — найду платёжки и прокладки по нему.", main_menu(d))
        elif data == "noop":
            pass
        elif data.startswith("list:"):
            page = int(data.split(":")[1])
            edit(chat, msg_id, "📂 Все платёжки (по числу прокладок):", list_page(d, page))
        elif data == "fav:0" or data.startswith("fav:"):
            uid = cb["from"]["id"]
            lst = fav_load().get(str(uid), [])
            if not lst:
                edit(chat, msg_id, "⭐ <b>Избранное</b>\n\nПока пусто. Открой любую платёжку и нажми «⭐ В избранное».",
                     main_menu(d))
                return
            kb = {"inline_keyboard": []}
            row = []
            for dom in lst[:48]:
                g = d.get(dom) or {"name": dom}
                row.append(ebtn(type_emoji(g.get("type", "")), (g.get("name") or dom)[:24], cb=f"gw:{dom}"))
                if len(row) == 2:
                    kb["inline_keyboard"].append(row)
                    row = []
            if row:
                kb["inline_keyboard"].append(row)
            kb["inline_keyboard"].append([btn("🏠 В меню", cb="menu", style="primary")])
            edit(chat, msg_id, f"⭐ <b>Избранное</b> — {len(lst)}:", kb)
        elif data == "trash:0":
            items = [(dom, g) for dom, g in d.items() if is_trashed(g)]
            if not items:
                edit(chat, msg_id, "🗑 <b>Корзина пуста</b> — всё чисто.", main_menu(d))
                return
            kb = {"inline_keyboard": []}
            row = []
            for dom, g in items[:48]:
                row.append(btn((g.get("name") or dom)[:24], cb=f"gw:{dom}"))
                if len(row) == 2:
                    kb["inline_keyboard"].append(row); row = []
            if row:
                kb["inline_keyboard"].append(row)
            kb["inline_keyboard"].append([btn("🏠 В меню", cb="menu", style="primary")])
            edit(chat, msg_id, f"🗑 <b>Корзина</b> — {len(items)} (открой и восстанови):", kb)
        elif data.startswith("trash:") and not data.startswith("trashrestore:"):
            dom = data.split(":", 1)[1]
            g = d.get(dom)
            if g:
                g["trashed"] = {"reason": "убрано вручную", "ts": int(time.time())}
                json.dump(d, open(DATA_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
                edit(chat, msg_id, f"🗑 «{g.get('name', dom)}» убрано в корзину.", main_menu(d))
        elif data.startswith("trashrestore:"):
            dom = data.split(":", 1)[1]
            g = d.get(dom)
            if g:
                g.pop("trashed", None)
                json.dump(d, open(DATA_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
                edit(chat, msg_id, gateway_card_text(dom, g)[:3800], kb_url(g.get("partners", []), 0, dom, cat_of(g)))
        elif data.startswith("favadd:"):
            dom = data.split(":", 1)[1]
            uid = cb["from"]["id"]
            act, lst = fav_toggle(uid, dom)
            g = d.get(dom, {})
            edit(chat, msg_id, f"⭐ {act} «{g.get('name', dom)}» в избранное ({len(lst)}).",
                 kb_url(g.get("partners", []), 0, dom, cat_of(g), is_trashed(g)))
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
                 kb_url(g.get("partners", []), 0, dom, cat_of(g), is_trashed(g)))
        elif data.startswith("p:"):
            _, dom, page, cat = data.split(":")
            g = d.get(dom)
            if not g:
                return
            edit(chat, msg_id, gateway_card_text(dom, g)[:3800],
                 kb_url(g.get("partners", []), int(page), dom, cat, is_trashed(g)))


def list_page(d, page=0):
    items = sorted([kv for kv in d.items() if not is_trashed(kv[1])], key=lambda kv: -len(kv[1].get("partners", [])))
    pages = max(1, -(-len(items) // PAGE_SIZE))
    page = min(max(page, 0), pages - 1)
    chunk = items[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    kb = {"inline_keyboard": []}
    row = []
    for dom, g in chunk:
        row.append(ebtn(type_emoji(g.get('type','')),
                        f"{g.get('name', dom)[:20]} ({len(g.get('partners', []))})",
                        cb=f"gw:{dom}"))
        if len(row) == 2:
            kb["inline_keyboard"].append(row)
            row = []
    if row:
        kb["inline_keyboard"].append(row)
    nav = []
    if page > 0:
        nav.append(btn("◀ Назад", cb=f"list:{page - 1}", style="primary"))
    nav.append(btn(f"{page + 1}/{pages}", cb="noop"))
    if page < pages - 1:
        nav.append(btn("Ещё ▶", cb=f"list:{page + 1}", style="success"))
    kb["inline_keyboard"].append(nav)
    kb["inline_keyboard"].append([btn("🏠 В меню", cb="menu", style="primary")])
    return kb


def search_results(d, q):
    ql = q.lower()
    hits = []
    for dom, g in d.items():
        if is_trashed(g):
            continue
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
