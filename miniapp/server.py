#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Мини-сервер Mini App: статика + /api/chat (команды по каталогу)."""
import json
import re
import subprocess
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path("/var/www/html/app")
DATA = Path("/opt/crypto-ramp-monitor/gateway_parser/data.json")
REPO = Path("/opt/crypto-ramp-monitor")


def load():
    try:
        return json.loads(DATA.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save(d):
    DATA.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def cat_of(g):
    t = (g.get("type") or "").lower()
    for k, kw in (("gift", "гифт"), ("gift", "ключ"), ("swap", "обменник"), ("exchange", "биржа"),
                  ("wallet", "кошел"), ("processor", "процессор"), ("stable", "стабил"),
                  ("gateway", "шлюз"), ("defi", "defi"), ("nft", "nft"), ("game", "гейминг"),
                  ("merch", "мерчант"), ("integ", "интеграц"), ("site", "сайт")):
        if kw in t:
            return k
    return "other"


def fmt_links(items, limit=12):
    out = []
    for dom, g in items[:limit]:
        out.append(f"• <b>{g.get('name', dom)}</b> — {dom} ({len(g.get('partners', []))})")
    return "\n".join(out)


def handle(text):
    d = load()
    t = text.strip()
    low = t.lower()

    if low in ("помощь", "help", "?", "команды"):
        return ("🧭 Команды:\n"
                "• <b>найди X</b> — поиск по каталогу\n"
                "• <b>wert</b> / <b>paybis</b> — прокладки платёжки\n"
                "• <b>статистика</b> — сколько всего\n"
                "• <b>гифты</b> / <b>биржи</b> / <b>кошельки</b> — раздел\n"
                "• <b>добавь site.com [название]</b> — добавить сайт\n"
                "• <b>ссылки</b> — топ-20 по прокладкам\n"
                "• <b>запусти охотников по &lt;тема&gt;</b> — поиск и добавление сайтов")

    if low.startswith(("найди", "поиск", "search")):
        q = re.sub(r"^(найди|поиск|search)\s*", "", low).strip()
        if not q:
            return "Напиши: найди wert"
        hits = [(dom, g) for dom, g in d.items()
                if q in (g.get("name", "") + " " + dom + " " + (g.get("type") or "") + " " +
                         " ".join(p.get("name", "") for p in g.get("partners", []))).lower()]
        hits.sort(key=lambda kv: -len(kv[1].get("partners", [])))
        if not hits:
            return f"🤷 По «{q}» ничего нет."
        return f"🔎 Нашёл {len(hits)}:\n{fmt_links(hits)}"

    if low in ("статистика", "stats", "сколько"):
        total_p = sum(len(g.get("partners", [])) for g in d.values())
        cats = {}
        for g in d.values():
            cats[cat_of(g)] = cats.get(cat_of(g), 0) + 1
        top = "\n".join(f"• {k}: {v}" for k, v in sorted(cats.items(), key=lambda x: -x[1]))
        return (f"📊 В каталоге: <b>{len(d)}</b> карточек, <b>{total_p}</b> связей.\n\n{top}")

    if low in ("ссылки", "links", "топ"):
        items = sorted(d.items(), key=lambda kv: -len(kv[1].get("partners", [])))
        return "🔗 Топ по прокладкам:\n" + fmt_links(items, 20)

    if re.search(r"(запусти|запустить|начни|start)\s*(охот|hunt)", low) or low.startswith(("охоться", "охотиться", "hunt ")):
        topic = re.sub(r"^(запусти|запустить|начни|start|охоться|охотиться|hunt)\s*(охотник\w*|hunt\w*)?\s*(по|на|за|for)?\s*", "", t, flags=re.I).strip()
        topic = topic or "crypto payment gateway"
        try:
            proc = subprocess.run(["/usr/bin/python3", str(REPO / "miniapp" / "hunter.py"), topic],
                                  capture_output=True, timeout=240)
            out = proc.stdout.decode("utf-8", "ignore").strip().splitlines()
            res = json.loads(out[-1]) if out else {}
            added = res.get("added", [])
            if not added:
                return f"🕵️ Охотился по «{topic}», проверил {res.get('checked', 0)} доменов — новых не нашёл."
            return (f"🕵️ Охота по «{topic}»: проверил {res.get('checked', 0)}, добавил {len(added)}:\n" +
                    "\n".join(f"• {a}" for a in added) + "\n\nОни уже в каталоге и на GitHub.")
        except subprocess.TimeoutExpired:
            return f"🕵️ Охота по «{topic}» идёт долго — запустил в фоне, результаты появятся в каталоге."
        except Exception as e:
            return f"⚠️ Охотник упал: {e}"

    if low.startswith("добавь") or low.startswith("add "):
        m = re.search(r"(https?://)?([a-z0-9-]+\.[a-z]{2,})", low)
        if not m:
            return "Напиши: добавь site.com"
        dom = m.group(2)
        if dom in d:
            return f"Уже есть: {dom}"
        name = re.sub(r"^(добавь|add)\s*", "", t).replace(m.group(0), "").strip() or dom
        d[dom] = {"name": name[:40], "type": "сайт", "fees": "—",
                  "kyc": {"обязателен": "уточняется", "лимиты": "—", "уровни": []},
                  "notes": "Добавлено через Mini App", "partners": []}
        save(d)
        try:
            subprocess.run(["git", "-C", str(REPO), "add", "-A"], capture_output=True, timeout=20)
            subprocess.run(["git", "-C", str(REPO), "-c", "user.name=miniapp", "-c", "user.email=miniapp@local",
                            "commit", "-qm", f"miniapp: +{dom}"], capture_output=True, timeout=20)
            subprocess.run(["git", "-C", str(REPO), "push", "-q", "origin", "main"], capture_output=True, timeout=40)
        except Exception:
            pass
        return f"✅ Добавил <b>{name}</b> ({dom}) и запушил."

    # прямой запрос домена
    key = low.replace(" ", "")
    for dom, g in d.items():
        if key == dom.split(".")[0] or key in dom:
            ps = g.get("partners", [])
            body = "\n".join(f"• {p.get('name')} — {p.get('url')}" for p in ps[:15])
            return (f"{g.get('name', dom)} ({dom})\n🏷 {g.get('type','—')}\n"
                    f"🛂 KYC: {g.get('kyc',{}).get('обязателен','—')}\n"
                    f"💸 {g.get('fees','—')}\n\n🔗 Прокладки ({len(ps)}):\n{body}")

    # раздел
    for k, label in (("gift", "гифты"), ("exchange", "биржи"), ("wallet", "кошельки"), ("gateway", "шлюзы"),
                     ("swap", "обменники"), ("processor", "процессоры"), ("defi", "defi")):
        if low == label:
            items = [(dom, g) for dom, g in d.items() if cat_of(g) == k]
            items.sort(key=lambda kv: -len(kv[1].get("partners", [])))
            return f"📂 {label.title()} — {len(items)}:\n{fmt_links(items)}"

    return ("🤖 Понимаю команды:\n"
            "• найди wert — поиск\n• запусти охотников по гифт-карты — охота и добавление\n"
            "• добавь site.com — вручную добавить\n• статистика / ссылки / гифты / биржи / кошельки\n"
            "Напиши «помощь».")


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html"):
            f = ROOT / "index.html"
        elif path == "/data.json":
            f = DATA
        else:
            f = ROOT / path.lstrip("/")
        if f.exists() and f.is_file():
            ctype = "application/json; charset=utf-8" if f.suffix == ".json" else "text/html; charset=utf-8"
            self._send(200, f.read_bytes(), ctype)
        else:
            self._send(404, '{"error":"not found"}')

    def do_OPTIONS(self):
        self._send(204, b"")

    def do_POST(self):
        if urllib.parse.urlparse(self.path).path != "/api/chat":
            return self._send(404, '{"error":"not found"}')
        n = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            payload = {}
        text = (payload.get("text") or "")[:500]
        try:
            reply = handle(text)
        except Exception as e:
            reply = f"⚠️ Ошибка: {e}"
        self._send(200, json.dumps({"reply": reply}, ensure_ascii=False))


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8787), H).serve_forever()
