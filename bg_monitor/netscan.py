#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Реальный скан: открывает сайт в chromium и ловит запросы к платёжным виджетам."""
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

DATA = Path("/opt/crypto-ramp-monitor/gateway_parser/data.json")

PROVIDERS = {
    "Swapped": ["swapped.com", "api.swapped"],
    "Paybis": ["widget.paybis.com", "paybis.com"],
    "Wert": ["widget.wert.io", "wert.io"],
    "MoonPay": ["moonpay.com", "buy.moonpay"],
    "Transak": ["transak.com", "global.transak"],
    "Mercuryo": ["mercuryo.io", "mercuryo.co"],
    "Banxa": ["banxa.com"],
    "Onramper": ["onramper.com"],
    "Ramp": ["ramp.network"],
    "Simplex": ["simplex.com"],
    "Utorg": ["utorg.pro", "utorg.io"],
    "Guardarian": ["guardarian.com"],
    "Alchemy Pay": ["alchemypay.org"],
    "Topper": ["topperpay.com"],
    "Kado": ["kado.money"],
    "Swipelux": ["swipelux.com"],
    "Stripe": ["js.stripe.com", "checkout.stripe.com"],
    "Adyen": ["adyen.com"],
    "Braintree": ["braintreegateway.com"],
    "Nuvei": ["nuvei.com", "safecharge"],
    "Checkout.com": ["checkout.com/sdk", "checkoutcdn.com"],
    "Sumsub": ["sumsub.com"],
    "Onfido": ["onfido.com", "onfido-sdk"],
    "Jumio": ["jumio.com"],
    "Veriff": ["veriff.com", "veriff.me"],
    "Persona": ["withpersona.com"],
}


def scan(dom, timeout=25000):
    found = {}
    logs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = browser.new_context(user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                              "(KHTML, like Gecko) Chrome/126 Safari/537.36"))
        page = ctx.new_page()
        page.route("**/*", lambda route: route.abort()
                   if route.request.resource_type in ("image", "media", "font") else route.continue_())
        page.on("request", lambda r: logs.append(r.url))
        for path in ("", "/deposit", "/buy"):
            try:
                page.goto("https://" + dom + path, timeout=timeout, wait_until="domcontentloaded")
                page.wait_for_timeout(2500)
                # жмём Buy/Deposit/Pay, чтобы инициализировать виджет
                for label in ("Buy", "Deposit", "Pay", "Купить", "Пополнить", "Купить крипту"):
                    try:
                        el = page.get_by_text(label, exact=False).first
                        if el and el.is_visible():
                            el.click(timeout=2500)
                            page.wait_for_timeout(3500)
                            break
                    except Exception:
                        continue
            except Exception:
                pass
        try:
            content = page.content().lower()
        except Exception:
            content = ""
        browser.close()
    text = (" ".join(logs) + " " + content).lower()
    for name, needles in PROVIDERS.items():
        for n in needles:
            if n in text:
                found[name] = n
                break
    return found


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    d = json.loads(DATA.read_text(encoding="utf-8"))
    alive = [(dom, g) for dom, g in d.items() if not g.get("trashed")]
    # ротация: сначала те, что давно/никогда не сканились
    alive.sort(key=lambda kv: kv[1].get("net_scanned", 0))
    targets = [dom for dom, g in alive][:limit]
    out = {}
    for dom in targets:
        try:
            found = scan(dom)
        except Exception as e:
            found = {}
            print(f"  ! {dom}: {e}", file=sys.stderr)
        d[dom]["net_scanned"] = int(time.time())
        if found:
            out[dom] = found
            d[dom]["net_gateways"] = found
            print(f"✅ {dom}: {', '.join(found)}")
        else:
            print(f"— {dom}")
    if out:
        DATA.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"scanned": len(targets), "hits": len(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
