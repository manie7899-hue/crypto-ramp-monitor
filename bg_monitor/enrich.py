#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Обогащение каталога: методы оплаты, API и документация. Батчами по N доменов."""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE.parent / "gateway_parser" / "data.json"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36"}

PAY = {
    "visa": "Visa", "mastercard": "Mastercard", "maestro": "Maestro", "amex": "Amex",
    "american express": "Amex", "unionpay": "UnionPay", "jcb": "JCB", "discover": "Discover",
    "мир": "МИР", "mir card": "МИР", "сбп": "СБП", "sbp": "СБП", "юmoney": "ЮMoney", "yoomoney": "ЮMoney",
    "sepa": "SEPA", "swift": "SWIFT", "ach": "ACH", "apple pay": "Apple Pay", "google pay": "Google Pay",
    "paypal": "PayPal", "klarna": "Klarna", "sofort": "Sofort", "ideal": "iDEAL", "bancontact": "Bancontact",
    "paysafecard": "paysafecard", "skrill": "Skrill", "neteller": "Neteller", "neosurf": "Neosurf",
    "bitcoin": "Bitcoin", "usdt": "USDT", "usdc": "USDC", "ethereum": "Ethereum", "lightning": "Lightning",
    "alipay": "Alipay", "wechat": "WeChat Pay", "pix": "PIX", "boleto": "Boleto", "upi": "UPI",
}
PROVIDERS = {
    "stripe": "Stripe", "adyen": "Adyen", "braintree": "Braintree", "checkout.com": "Checkout.com",
    "nuvei": "Nuvei", "simplex": "Simplex", "moonpay": "MoonPay", "wert": "Wert", "transak": "Transak",
    "mercuryo": "Mercuryo", "banxa": "Banxa", "ramp": "Ramp", "onramper": "Onramper", "paybis": "Paybis",
    "alchemy pay": "Alchemy Pay", "alchemypay": "Alchemy Pay", "utorg": "Utorg", "guardarian": "Guardarian",
    "kado": "Kado", "swipelux": "Swipelux", "topper": "Topper", "paddle": "Paddle", "paypal": "PayPal",
    "klarna": "Klarna", "worldpay": "Worldpay", "bridgerpay": "BridgerPay", "unlimit": "Unlimit",
}


def fetch(url, limit=200000):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.read(limit).decode("utf-8", "ignore").lower()
    except Exception:
        return ""


def find_docs(dom, body):
    cands = []
    for m in re.findall(r'href="([^"]*(?:docs?|api|developer|reference)[^"]*)"', body):
        if m.startswith("http"):
            cands.append(m)
        elif m.startswith("/"):
            cands.append(f"https://{dom}{m}")
    for sub in ("docs", "developers", "api"):
        cands.append(f"https://{sub}.{dom}")
    cands.append(f"https://{dom}/docs")
    cands.append(f"https://{dom}/api")
    return cands


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    d = json.loads(DATA.read_text(encoding="utf-8"))
    todo = [(dom, g) for dom, g in d.items() if not g.get("enriched")]
    todo.sort(key=lambda kv: -len(kv[1].get("partners", [])))
    done = 0
    for dom, g in todo[:limit]:
        body = fetch("https://" + dom)
        if not body:
            body = fetch("http://" + dom)
        if not body:
            g["enriched"] = int(time.time())
            g["pay"] = g.get("pay", [])
            continue
        pays = sorted({v for k, v in PAY.items() if k in body})
        provs = sorted({v for k, v in PROVIDERS.items() if k in body})
        docs = ""
        api = ""
        for u in find_docs(dom, body):
            b2 = fetch(u, 60000)
            if b2 and len(b2) > 400:
                if "api" in u and not api:
                    api = u
                if ("doc" in u or "developer" in u or "reference" in u) and not docs:
                    docs = u
            if api and docs:
                break
        g["pay"] = pays[:12]
        g["providers"] = provs[:12]
        g["api"] = api
        g["docs"] = docs
        g["enriched"] = int(time.time())
        done += 1
    DATA.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"обогащено: {done} | осталось: {len(todo) - done}")


if __name__ == "__main__":
    main()
