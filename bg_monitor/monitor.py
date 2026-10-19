#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Фоновый мониторинг крипто-платёжек.
Каждый запуск (по cron, например каждые 30 минут):
  1. Ищет новые домены через Bing/DuckDuckGo/Mojeek (включая x.com/твиттер и форумы).
  2. Парсит RSS крипто-СМИ на предмет анонсов партнёрств/интеграций.
  3. Проверяет новые домены (живость, title, релевантность теме).
  4. Новые находки: добавляет в gateway_parser/data.json, пишет в new_finds.json
     и шлёт уведомление в Telegram-бота.
Работает на чистом stdlib — идеально для GitHub Actions (бесплатный хост).

Требует окружение (опционально): TG_BOT_TOKEN, TG_CHAT_ID.
Данные каталога: ../gateway_parser/data.json (или путь в DATA_JSON).
"""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA_PATH = Path(os.environ.get("DATA_JSON", str(BASE.parent / "gateway_parser" / "data.json")))
SEEN_PATH = BASE / "seen.json"
FINDS_PATH = BASE / "new_finds.json"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

QUERIES = [
    "crypto onramp partnership announcement",
    "new fiat onramp integrated wallet crypto",
    "crypto payment gateway partnership 2026",
    "instant swap exchange new partnership",
    "site:x.com crypto onramp partnership",
    "site:twitter.com onramp integrated crypto",
    "site:reddit.com new crypto onramp provider",
    "site:bitcointalk.org payment gateway partnership",
    "обменник криптовалют новое партнёрство",
    "купить криптовалюту картой новый сервис",
]

RSS_FEEDS = [
    ("Cointelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt", "https://decrypt.co/feed"),
    ("TheBlock", "https://www.theblock.co/rss.xml"),
    ("BitcoinMagazine", "https://bitcoinmagazine.com/feed"),
]

RSS_KEYWORDS = re.compile(
    r"(partner|integrat|on-?ramp|checkout|payment|crypto buy|fiat|stablecoin|acqui)",
    re.I)

DOMAIN_RE = re.compile(
    r"\b([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.(?:com|net|org|io|xyz|gg|app|co|fi|"
    r"finance|fun|me|money|pro|plus|exchange|link|global|zone|site))\b", re.I)

SKIP = re.compile(
    r"(^|\.)(google|bing|duckduckgo|mojeek|yandex|twitter|x\.com|reddit|youtube|"
    r"facebook|instagram|linkedin|tiktok|discord|telegram|t\.me|medium|wikipedia|"
    r"amazon|ebay|apple|github|cointelegraph|coindesk|decrypt|theblock|"
    r"bitcoinmagazine|coinmarketcap|coingecko|prnewswire|globenewswire|benzinga|"
    r"investing|yahoo|reuters|bloomberg|forbes|trustpilot|sitejabber|"
    r"cryptobriefing|cryptonews\.com|walletreviewer|news\.bitcoin|bitcoinist|"
    r"cryptoslate|cryptopotato|beincrypto|u\.today|thepaypers|finextra|pymnts|"
    r"crypto\.news|ambcrypto|coinjournal|cryptodaily|watcher\.guru|"
    r"livebitcoinnews|cryptonewsbtc|cryptoinsiders|bitcoin\.news|bitpush|"
    r"chaincatcher|foresightnews|panewslab|odaily|blockworks|thedefiant|"
    r"dlnews|protos|unchainedcrypto|bankless)\.", re.I)

RELEVANCE = ["crypto", "bitcoin", "ethereum", "onramp", "on-ramp", "fiat", "swap",
             "exchange", "payment", "wallet", "checkout", "stablecoin", "card",
             "крипт", "обмен", "кошел", "оплат", "покуп"]

KNOWN_DOMAINS = set()


def load_known() -> None:
    global KNOWN_DOMAINS
    try:
        d = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        KNOWN_DOMAINS.update(d.keys())
        for g in d.values():
            for p in g.get("partners", []):
                dom = domain_of(p.get("url", ""))
                if dom:
                    KNOWN_DOMAINS.add(dom)
    except Exception as e:
        print("[!] data.json:", e)


def domain_of(u: str) -> str:
    u = (u or "").strip()
    if not u.startswith("http"):
        u = "https://" + u
    try:
        dom = urllib.parse.urlparse(u).netloc.lower()
    except Exception:
        return ""
    dom = dom[4:] if dom.startswith("www.") else dom
    return dom.split(":")[0]


def load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_json(p: Path, obj) -> None:
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch(url: str, timeout: int = 12):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "text/html,application/xml;q=0.9,*/*;q=0.8",
                                               "Accept-Language": "en-US,en;q=0.8,ru;q=0.6"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.geturl(), r.read(300_000)
    except Exception:
        return None, None


# ---------------------------------------------------------------- поиск
def search_bing(q: str, n: int = 10) -> list:
    _, body = fetch("https://www.bing.com/search?q=" + urllib.parse.quote(q) + "&count=30")
    if not body:
        return []
    try:
        import re as _re
        links = _re.findall(rb'<h2[^>]*><a href="(https?://[^"]+)"', body)
        return [l.decode("utf-8", "ignore") for l in links[:n]]
    except Exception:
        return []


def search_ddg(q: str, n: int = 10) -> list:
    _, body = fetch("https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(q))
    if not body:
        return []
    out = []
    try:
        for m in re.finditer(rb'class="result__a"[^>]*href="([^"]+)"', body):
            href = m.group(1).decode("utf-8", "ignore")
            if href.startswith("//duckduckgo.com/l/"):
                href = urllib.parse.parse_qs(urllib.parse.urlparse("https:" + href).query).get("uddg", [href])[0]
            if href.startswith("http"):
                out.append(href)
    except Exception:
        pass
    return out[:n]


def search_mojeek(q: str, n: int = 10) -> list:
    _, body = fetch("https://www.mojeek.com/search?q=" + urllib.parse.quote(q))
    if not body:
        return []
    out = []
    try:
        for m in re.finditer(rb'<a class="ob" href="([^"]+)"', body):
            href = m.group(1).decode("utf-8", "ignore")
            if href.startswith("/redirect"):
                href = urllib.parse.unquote(href.split("url=", 1)[-1])
            if href.startswith("http"):
                out.append(href)
    except Exception:
        pass
    return out[:n]


def rss_items(url: str) -> list:
    _, body = fetch(url)
    if not body:
        return []
    try:
        root = ET.fromstring(body)
        items = []
        for it in root.iter("item"):
            title = "".join(t.text or "" for t in it.iter("title"))
            desc = "".join(t.text or "" for t in it.iter("description"))
            link = ""
            for l in it.iter("link"):
                link = l.text or ""
                break
            items.append((title, desc, link))
        return items
    except Exception:
        return []


def score(text: str) -> float:
    t = (text or "").lower()
    hits = [k for k in RELEVANCE if k in t]
    return round(len(hits) / len(RELEVANCE), 3)


def verify(dom: str) -> dict:
    final, body = fetch("https://" + dom)
    if body is None:
        final, body = fetch("https://www." + dom)
    if body is None:
        return {}
    txt = body.decode("utf-8", "ignore")
    title = ""
    m = re.search(r"<title[^>]*>(.*?)</title>", txt, re.S | re.I)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()[:160]
    m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', txt, re.S | re.I)
    desc = ""
    if m:
        desc = re.sub(r"\s+", " ", m.group(1)).strip()[:200]
    return {"url": final or ("https://" + dom), "title": title, "desc": desc,
            "score": score(title + " " + desc + " " + dom)}


def tg_send(text: str) -> bool:
    token = os.environ.get("TG_BOT_TOKEN", "").strip()
    chat = os.environ.get("TG_CHAT_ID", "").strip()
    if not token or not chat:
        try:
            cfg = json.loads((BASE / "tg_config.json").read_text(encoding="utf-8"))
            token = token or str(cfg.get("token", "")).strip()
            chat = chat or str(cfg.get("chat_id", "")).strip()
        except Exception:
            pass
    if not token or not chat:
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": chat, "text": text,
                                       "disable_web_page_preview": True}).encode()
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200
    except Exception as e:
        print("[!] TG:", e)
        return False


def auto_add_to_catalog(f: dict) -> None:
    """Добавляет находку в data.json базовой карточкой (для ручной доводки)."""
    try:
        d = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        return
    dom = f["domain"]
    if dom in d:
        return
    d[dom] = {
        "name": f["title"][:40] or dom,
        "type": "сайт (авто-находка)",
        "fees": "—",
        "kyc": {"обязателен": "не проверено", "лимиты": "—", "уровни": ["—"]},
        "notes": f"Найдено фоновым монитором {f['ts'][:10]}, источник: {f['source']}. "
                 f"Заголовок: {f['title']}",
        "partners": [],
    }
    DATA_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    load_known()
    seen = load_json(SEEN_PATH)
    finds = load_json(FINDS_PATH)
    if isinstance(finds, dict):
        finds = [finds] if finds else []
    candidates = {}  # domain -> source

    # 1) поисковики
    for q in QUERIES:
        for name, fn in (("bing", search_bing), ("ddg", search_ddg), ("mojeek", search_mojeek)):
            try:
                links = fn(q, 8)
            except Exception:
                links = []
            for l in links:
                dom = domain_of(l)
                if dom and not SKIP.search(dom):
                    candidates.setdefault(dom, f"search:{name}:{q[:40]}")
            time.sleep(0.8)

    # 2) RSS
    for src, url in RSS_FEEDS:
        for title, desc, link in rss_items(url):
            if RSS_KEYWORDS.search(title + " " + desc):
                for dom in DOMAIN_RE.findall(title + " " + desc + " " + link):
                    if dom and not SKIP.search(dom):
                        candidates.setdefault(dom, f"rss:{src}")
        time.sleep(0.5)

    # 3) проверка
    STRONG = ("onramp", "on-ramp", "checkout", "swap", "buy crypto", "sell crypto",
              "ramp", "payment", "exchange", "fiat", "крипт", "обмен", "покуп")
    new = []
    for dom in sorted(candidates):
        if dom in KNOWN_DOMAINS or dom in seen:
            continue
        info = verify(dom)
        strong_hit = any(k in (info.get("title", "") + " " + info.get("desc", "") + " " + dom).lower()
                         for k in STRONG)
        if not info or info["score"] < 0.15 or not strong_hit:
            seen[dom] = time.strftime("%Y-%m-%d %H:%M")
            continue
        f = {"domain": dom, "url": info["url"], "title": info["title"],
             "desc": info["desc"], "score": info["score"],
             "source": candidates[dom], "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
        new.append(f)
        seen[dom] = f["ts"]
        KNOWN_DOMAINS.add(dom)
        auto_add_to_catalog(f)
        time.sleep(0.3)

    if new:
        for f in new:
            finds.append(f)
            tg_send(f"🆕 {f['domain']}\n{f['title']}\nрелев: {f['score']:.2f}\n"
                    f"источник: {f['source']}\n{f['url']}")
            print(f"NEW {f['domain']} | {f['title'][:60]} | {f['source']}")
    else:
        print("ничего нового")

    save_json(SEEN_PATH, seen)
    save_json(FINDS_PATH, finds)
    print(f"итого находок в базе: {len(finds)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
