#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Технические отпечатки платёжных провайдеров: 3DS, чек-аут-скрипты, iframe-хосты."""
import re

PROVIDER_HOSTS = {
    "Stripe": [r"js\.stripe\.com", r"checkout\.stripe\.com", r"stripe\.network"],
    "Adyen": [r"adyen\.com", r"checkoutshopper", r"acs\.adyen"],
    "Braintree": [r"braintreegateway\.com", r"braintree-api\.com", r"assets\.braintreegateway"],
    "Checkout.com": [r"checkout\.com/sdk", r"checkoutcdn\.com", r"ckocdn"],
    "Nuvei": [r"nuvei\.com", r"safeCharge".lower(), r"ccapi\d*\.nuvei"],
    "Worldpay": [r"worldpay\.com", r"rbsworldpay", r"secure\.worldpay"],
    "PayPal": [r"paypalobjects\.com", r"paypal\.com/sdk", r"paypal\.com/webapps"],
    "Klarna": [r"klarna\.com", r"klarna-checkout", r"x\.klarna"],
    "MoonPay": [r"buy\.moonpay\.com", r"moonpay\.com"],
    "Wert": [r"widget\.wert\.io", r"wert\.io"],
    "Transak": [r"transak\.com", r"global\.transak"],
    "Mercuryo": [r"mercuryo\.io"],
    "Banxa": [r"banxa\.com"],
    "Ramp": [r"ramp\.network"],
    "Onramper": [r"onramper\.com"],
    "Paybis": [r"paybis\.com"],
    "Simplex": [r"simplex\.com"],
    "Alchemy Pay": [r"alchemypay\.org"],
    "Unlimit": [r"unlimit\.com"],
    "BridgerPay": [r"bridgerpay\.com"],
    "Apple Pay": [r"applepay", r"apple-pay"],
    "Google Pay": [r"google\.com/pay", r"pay\.google"],
}

THREEDS = [r"3d[\s-]?secure", r"3ds2?", r"three[_\s-]?d[_\s-]?secure", r"pareq", r"creq",
           r"acs[_\s-]?url", r"acsurl", r"verified by visa", r"mastercard securecode",
           r"authentication\s*required", r"challenge\s*flow", r"threedsmethod"]

CHECKOUT_PATHS = ["/checkout", "/pay", "/buy", "/cart", "/payment", "/order", "/purchase"]


def detect(raw, domain=""):
    """Возвращает {'gateways': {name: evidence}, '3ds': bool, '3ds_evidence': str}"""
    low = raw.lower()
    gws = {}
    for name, pats in PROVIDER_HOSTS.items():
        for p in pats:
            if re.search(p, low):
                gws[name] = p
                break
    tds = ""
    for p in THREEDS:
        m = re.search(p, low)
        if m:
            tds = m.group(0)
            break
    return {"gateways": gws, "3ds": bool(tds), "3ds_evidence": tds}
