#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Обогащение каталога v2: методы оплаты по группам, регионы, лицензии, комиссии, KYC, API."""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from fingerprints import detect, CHECKOUT_PATHS
except Exception:
    detect = None
    CHECKOUT_PATHS = []

BASE = Path(__file__).resolve().parent
DATA = BASE.parent / "gateway_parser" / "data.json"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36"}

GROUPS = {
    "card": {"visa": "Visa", "mastercard": "Mastercard", "maestro": "Maestro", "amex": "Amex",
             "american express": "Amex", "unionpay": "UnionPay", "jcb": "JCB",
             "diners": "Diners", "мир": "МИР"},
    "wallet": {"apple pay": "Apple Pay", "google pay": "Google Pay", "paypal": "PayPal", "skrill": "Skrill",
               "neteller": "Neteller", "юmoney": "ЮMoney", "yoomoney": "ЮMoney", "payoneer": "Payoneer",
               "perfect money": "Perfect Money", "payeer": "Payeer"},
    "bank": {"sepa": "SEPA", "swift": "SWIFT", "ach": "ACH", "faster payments": "Faster Payments",
             "pix": "PIX", "boleto": "Boleto", "upi": "UPI", "сбп": "СБП", "sbp": "СБП", "ideal": "iDEAL",
             "sofort": "Sofort", "bancontact": "Bancontact", "giropay": "Giropay", "przelewy24": "Przelewy24",
             "paysera": "Paysera", "klarna": "Klarna", "trustly": "Trustly"},
    "crypto": {"bitcoin": "Bitcoin", "ethereum": "Ethereum", "usdt": "USDT", "usdc": "USDC", "lightning": "Lightning",
               "litecoin": "Litecoin", "tron": "TRON", "ton": "TON", "solana": "Solana", "bnb": "BNB",
               "polygon": "Polygon", "xrp": "XRP", "dogecoin": "Dogecoin"},
    "local": {"alipay": "Alipay", "wechat": "WeChat Pay", "paysafecard": "paysafecard", "neosurf": "Neosurf",
              "mobile money": "Mobile Money", "m-pesa": "M-Pesa", "pix": "PIX",
              "blik": "BLIK", "boleto": "Boleto", "qiwi": "QIWI", "elecsnet": "Элекснет"},
}
PROVIDERS = {"stripe": "Stripe", "adyen": "Adyen", "braintree": "Braintree", "checkout.com": "Checkout.com",
             "nuvei": "Nuvei", "simplex": "Simplex", "moonpay": "MoonPay", "wert": "Wert", "transak": "Transak",
             "mercuryo": "Mercuryo", "banxa": "Banxa", "ramp": "Ramp", "onramper": "Onramper", "paybis": "Paybis",
             "alchemy pay": "Alchemy Pay", "alchemypay": "Alchemy Pay", "utorg": "Utorg",
             "guardarian": "Guardarian", "kado": "Kado", "swipelux": "Swipelux", "topper": "Topper",
             "paddle": "Paddle", "worldpay": "Worldpay", "bridgerpay": "BridgerPay", "unlimit": "Unlimit"}
REGIONS = {"europe": "Европа", "european union": "ЕС", "eea": "ЕЭЗ", "united states": "США", "usa": "США",
           "united kingdom": "UK", "asia": "Азия", "latin america": "ЛатАм", "africa": "Африка",
           "middle east": "Ближний Восток", "cis": "СНГ", "russia": "Россия", "india": "Индия",
           "nigeria": "Нигерия", "brazil": "Бразилия", "turkey": "Турция", "worldwide": "Весь мир",
           "global": "Весь мир", "180 countries": "180+ стран", "190 countries": "190+ стран"}
LICENSES = {"fca": "FCA (UK)", "finCEN": "FinCEN (US)", "fintrac": "FINTRAC (CA)", "mica": "MiCA (ЕС)",
            "vasp": "VASP", "msb": "MSB", "pci dss": "PCI DSS", "pci-dss": "PCI DSS", "estonia": "Эстония (лицензия)",
            "lithuania": "Литва (лицензия)", "cysec": "CySEC", "mas": "MAS (Сингапур)", "asic": "ASIC (AU)"}


def has_kw(body, kw):
    kw = kw.strip()
    if not kw:
        return False
    if re.search(r"[а-яё]", kw):
        return kw in body
    return re.search(r"(?<![a-z0-9])" + re.escape(kw) + r"(?![a-z0-9])", body) is not None


def fetch(url, limit=250000):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.read(limit).decode("utf-8", "ignore")
    except Exception:
        return ""


def find_docs(dom, body):
    cands = []
    for m in re.findall(r'href="([^"]*(?:docs?|api|developer|reference)[^"]*)"', body, re.I):
        if m.startswith("http"):
            cands.append(m)
        elif m.startswith("/"):
            cands.append(f"https://{dom}{m}")
    for sub in ("docs", "developers", "api"):
        cands.append(f"https://{sub}.{dom}")
    cands += [f"https://{dom}/docs", f"https://{dom}/api", f"https://{dom}/developers"]
    return cands[:8]


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    d = json.loads(DATA.read_text(encoding="utf-8"))
    todo = [(dom, g) for dom, g in d.items() if not g.get("gateways_detected")]
    todo.sort(key=lambda kv: -len(kv[1].get("partners", [])))
    done = 0
    for dom, g in todo[:limit]:
        raw = fetch("https://" + dom) or fetch("http://" + dom)
        if not raw:
            g["fail"] = int(g.get("fail", 0)) + 1
            if g["fail"] >= 2 and not g.get("trashed"):
                g["trashed"] = {"reason": "сайт не отвечает (2 проверки)", "ts": int(time.time())}
                g["enriched"] = int(time.time())
            continue
        g.pop("fail", None)
        body = raw.lower()
        groups = {}
        for gk, mapping in GROUPS.items():
            vals = sorted({v for k, v in mapping.items() if has_kw(body, k)})
            if vals:
                groups[gk] = vals[:10]
        provs = sorted({v for k, v in PROVIDERS.items() if has_kw(body, k)})
        regions = sorted({v for k, v in REGIONS.items() if has_kw(body, k)})
        lic = sorted({v for k, v in LICENSES.items() if has_kw(body, k)})
        # комиссия
        fee = ""
        for m in re.finditer(r"(?:fee|комисси\w*)[^\d%]{0,30}(\d+(?:[.,]\d+)?)\s?%", body):
            try:
                val = float(m.group(1).replace(",", "."))
            except Exception:
                continue
            if 0 <= val <= 25:
                fee = f"{val:g}%"
                break
        # kyc
        kyc_note = ""
        if re.search(r"(no kyc|without kyc|без kyc|без верификаци)", body):
            kyc_note = "без KYC"
        elif re.search(r"(kyc required|verify your identity|пройти верификаци)", body):
            kyc_note = "KYC обязателен"
        # API-признаки
        api_kind = ""
        if re.search(r"(rest api|restful)", body):
            api_kind = "REST"
        elif "graphql" in body:
            api_kind = "GraphQL"
        sandbox = bool(re.search(r"(sandbox|test environment|тестов)", body))
        docs = api = ""
        for u in find_docs(dom, raw):
            b2 = fetch(u, 80000)
            if b2 and len(b2) > 400:
                lb = b2.lower()
                if not api and ("api" in u.lower() or "api" in lb[:3000]):
                    api = u
                if not docs and any(w in u.lower() for w in ("doc", "developer", "reference")):
                    docs = u
            if api and docs:
                break
        if detect:
            gws, tds, tds_ev = {}, False, ""
            fp = detect(raw)
            gws.update(fp["gateways"])
            tds = fp["3ds"]; tds_ev = fp["3ds_evidence"]
            extra = []
            for m in re.finditer(r'href="([^"]*(?:checkout|/pay|/buy|payment|purchase)[^"]*)"', raw, re.I):
                u = m.group(1)
                if u.startswith("http") and dom in u:
                    extra.append(u)
                elif u.startswith("/"):
                    extra.append(f"https://{dom}{u}")
            for u in extra[:3]:
                if gws and tds:
                    break
                page = fetch(u, 150000)
                if not page:
                    continue
                fp2 = detect(page)
                for k, v in fp2["gateways"].items():
                    gws.setdefault(k, "buy:" + v)
                if fp2["3ds"] and not tds:
                    tds = True; tds_ev = "buy:" + fp2["3ds_evidence"]
            for path in CHECKOUT_PATHS:
                if gws and tds:
                    break
                page = fetch(f"https://{dom}{path}", 150000)
                if not page:
                    continue
                fp2 = detect(page)
                for k, v in fp2["gateways"].items():
                    gws.setdefault(k, path + ":" + v)
                if fp2["3ds"] and not tds:
                    tds = True; tds_ev = path + ":" + fp2["3ds_evidence"]
            g["gateways_detected"] = [{"name": k, "evidence": v} for k, v in gws.items()][:8]
            if fp.get("kyc"):
                g["kyc_vendors"] = [{"name": k, "evidence": v} for k, v in fp["kyc"].items()][:6]
            if fp.get("kyc_words"):
                g["kyc_words"] = fp["kyc_words"]
            g["tds"] = tds
            if tds_ev:
                g["tds_evidence"] = tds_ev
        g["pay_groups"] = groups
        g["pay"] = sorted({v for vs in groups.values() for v in vs})[:14]
        g["providers"] = provs[:10]
        g["regions"] = regions[:6]
        g["licenses"] = lic[:6]
        if fee:
            g["fee_note"] = fee
        if kyc_note:
            g["kyc_note"] = kyc_note
        if api_kind:
            g["api_kind"] = api_kind
        g["sandbox"] = sandbox
        g["docs"] = docs
        g["api"] = api
        g["enriched"] = int(time.time())
        done += 1
    DATA.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"обогащено v2: {done} | осталось: {len(todo) - done}")


if __name__ == "__main__":
    main()
