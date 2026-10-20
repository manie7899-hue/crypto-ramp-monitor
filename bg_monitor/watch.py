#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Слежка за сменой платёжного шлюза/методов оплаты на сайтах. Шлёт диффы в Telegram."""
import json
import time
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE.parent / "gateway_parser" / "data.json"
CHANGES = BASE / "changes.json"
STATE = BASE / "watch_state.json"
CFG = json.loads((BASE / "tg_config.json").read_text(encoding="utf-8"))
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36"}

PAY = ["visa", "mastercard", "maestro", "amex", "american express", "unionpay", "jcb", "discover", "мир",
       "сбп", "юmoney", "yoomoney", "sepa", "swift", "ach", "apple pay", "google pay", "paypal", "klarna",
       "sofort", "ideal", "bancontact", "paysafecard", "skrill", "neteller", "neosurf", "bitcoin", "usdt",
       "usdc", "ethereum", "lightning", "alipay", "wechat", "pix", "boleto", "upi"]
PROV = ["stripe", "adyen", "braintree", "checkout.com", "nuvei", "simplex", "moonpay", "wert", "transak",
        "mercuryo", "banxa", "ramp", "onramper", "paybis", "alchemy pay", "alchemypay", "utorg",
        "guardarian", "kado", "swipelux", "topper", "paddle", "worldpay", "bridgerpay", "unlimit"]


def fetch(url, limit=200000):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.read(limit).decode("utf-8", "ignore").lower()
    except Exception:
        return ""


def tg(text):
    try:
        data = urllib.parse.urlencode({"chat_id": CFG["chat_id"], "text": text[:4000],
                                       "disable_web_page_preview": "true"}).encode()
        urllib.request.urlopen(urllib.request.Request(
            f"https://api.telegram.org/bot{CFG['token']}/sendMessage", data=data), timeout=20)
    except Exception as e:
        print("tg err", e)


import urllib.parse  # noqa: E402


def main():
    limit = int(__import__("sys").argv[1]) if len(__import__("sys").argv) > 1 else 20
    d = json.loads(DATA.read_text(encoding="utf-8"))
    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        state = {}
    try:
        changes = json.loads(CHANGES.read_text(encoding="utf-8"))
    except Exception:
        changes = []
    items = [(dom, g) for dom, g in d.items() if g.get("enriched")]
    items.sort(key=lambda kv: kv[1].get("enriched", 0))
    new_changes = 0
    for dom, g in items[:limit]:
        body = fetch("https://" + dom) or fetch("http://" + dom)
        if not body:
            continue
        pays = {p for p in PAY if p in body}
        provs = {p for p in PROV if p in body}
        cur = {"pay": sorted(pays), "prov": sorted(provs)}
        try:
            import sys as _s, pathlib as _pl
            _s.path.insert(0, str(_pl.Path(__file__).resolve().parent))
            from fingerprints import detect
            fp = detect(body)
            cur["gw"] = sorted(fp["gateways"].keys())
            cur["tds"] = fp["3ds"]
        except Exception:
            cur["gw"] = []
            cur["tds"] = False
        prev = state.get(dom)
        state[dom] = cur
        if prev:
            gone = sorted(set(prev.get("prov", [])) - set(cur["prov"]))
            came = sorted(set(cur["prov"]) - set(prev.get("prov", [])))
            pays_gone = sorted(set(prev.get("pay", [])) - set(cur["pay"]))
            pays_came = sorted(set(cur["pay"]) - set(prev.get("pay", [])))
            gw_minus = sorted(set(prev.get("gw", [])) - set(cur.get("gw", [])))
            gw_plus = sorted(set(cur.get("gw", [])) - set(prev.get("gw", [])))
            tds_changed = prev.get("tds") != cur.get("tds")
            if gone or came or pays_gone or pays_came or gw_minus or gw_plus or tds_changed:
                rec = {"ts": int(time.time()), "domain": dom, "name": g.get("name", dom),
                       "prov_minus": gone, "prov_plus": came,
                       "pay_minus": pays_gone, "pay_plus": pays_came}
                changes.insert(0, rec)
                new_changes += 1
                msg = (f"🔄 Изменение на {g.get('name', dom)} ({dom})\n")
                if gone:
                    msg += f"➖ шлюз: {', '.join(gone)}\n"
                if came:
                    msg += f"➕ шлюз: {', '.join(came)}\n"
                if pays_gone:
                    msg += f"➖ оплата: {', '.join(pays_gone)}\n"
                if pays_came:
                    msg += f"➕ оплата: {', '.join(pays_came)}\n"
                if gw_minus:
                    msg += f"➖ шлюз по коду: {', '.join(gw_minus)}\n"
                if gw_plus:
                    msg += f"➕ шлюз по коду: {', '.join(gw_plus)}\n"
                if tds_changed:
                    msg += f"🔐 3D-Secure: {'появился' if cur.get('tds') else 'пропал'}"
                tg(msg)
    STATE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    CHANGES.write_text(json.dumps(changes[:500], ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"проверено: {min(limit, len(items))} | изменений: {new_changes}")


if __name__ == "__main__":
    main()
