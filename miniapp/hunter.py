#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Охотник Mini App: ищет сайты по теме, проверяет живость и добавляет в каталог."""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

DATA = Path("/opt/crypto-ramp-monitor/gateway_parser/data.json")
REPO = Path("/opt/crypto-ramp-monitor")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
SKIP = {"google", "bing", "duckduckgo", "mojeek", "yandex", "wikipedia", "youtube", "reddit", "medium",
        "twitter", "x.com", "facebook", "instagram", "linkedin", "t.me", "github", "apple", "amazon",
        "coingecko", "coinmarketcap", "cointelegraph", "coindesk", "decrypt", "theblock", "cryptonews",
        "bitcoinist", "cryptopotato", "beincrypto", "cryptoslate", "u.today", "benzinga", "globenewswire",
        "prnewswire", "investing.com", "yahoo.com", "trustpilot", "wikipedia.org", "coinpaprika",
        "coinranking", "dextools", "pump.fun", "cryptorank", "coinmarketcap.com", "apps.apple.com",
        "play.google.com", "chromewebstore.google.com", "w3.org", "schema.org", "cloudflare.com"}


def fetch(url, limit=300000):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=12) as r:
            return r.read(limit).decode("utf-8", "ignore")
    except Exception:
        return ""


def search(query, engine="bing"):
    q = urllib.parse.quote(query)
    if engine == "bing":
        url = f"https://www.bing.com/search?q={q}&count=30"
    elif engine == "ddg":
        url = f"https://html.duckduckgo.com/html/?q={q}"
    else:
        url = f"https://www.mojeek.com/search?q={q}"
    return fetch(url)


def domains_from(html):
    ds = re.findall(r"https?://([a-z0-9-]+\.(?:com|net|org|io|xyz|gg|app|co|fi|finance|fun|me|ai|money|pro|site|ru|dev|so|to))\b", html)
    out = []
    for d in ds:
        d = d.lower().lstrip("www.")
        if any(s in d for s in SKIP):
            continue
        if d not in out:
            out.append(d)
    return out


def verify(domain):
    for scheme in ("https://", "http://"):
        body = fetch(scheme + domain, 60000).lower()
        if body and len(body) > 400:
            return body
    return ""


def main():
    topic = " ".join(sys.argv[1:]).strip() or "crypto payment gateway"
    d = json.loads(DATA.read_text(encoding="utf-8"))
    queries = [topic, f"{topic} сайт", f"{topic} review", f"best {topic}"]
    cands = []
    for q in queries:
        for eng in ("bing", "ddg"):
            html = search(q, eng)
            for dom in domains_from(html):
                if dom not in d and dom not in cands:
                    cands.append(dom)
            time.sleep(0.5)
        if len(cands) >= 25:
            break
    added, checked = [], 0
    for dom in cands[:30]:
        body = verify(dom)
        checked += 1
        if not body:
            continue
        title = ""
        m = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
        if m:
            title = re.sub(r"\s+", " ", m.group(1)).strip()[:60]
        d[dom] = d.get(dom) or {
            "name": title or dom, "type": "сайт (находка Mini App)", "fees": "—",
            "kyc": {"обязателен": "уточняется", "лимиты": "—", "уровни": []},
            "notes": f"Найдено охотником по теме: {topic}", "partners": []}
        added.append(dom)
    if added:
        DATA.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            import subprocess
            subprocess.run(["git", "-C", str(REPO), "add", "-A"], capture_output=True, timeout=20)
            subprocess.run(["git", "-C", str(REPO), "-c", "user.name=hunter", "-c", "user.email=hunter@local",
                            "commit", "-qm", f"hunter: +{len(added)} ({topic})"], capture_output=True, timeout=20)
            subprocess.run(["git", "-C", str(REPO), "push", "-q", "origin", "main"], capture_output=True, timeout=40)
        except Exception:
            pass
    print(json.dumps({"topic": topic, "checked": checked, "added": added}, ensure_ascii=False))


if __name__ == "__main__":
    main()
