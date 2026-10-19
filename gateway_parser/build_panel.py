#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Собирает panel.html + gateways.txt — каталог платёжных шлюзов:
KYC-инфо по каждому шлюзу + РАСКРЫВАЮЩАЯСЯ менюшка со ВСЕМИ «прокладками»
(кошельки, сайты, биржи, NFT, DeFi), где этот шлюз встроен.

Запуск: python3 build_panel.py
"""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = json.loads((BASE / "data.json").read_text(encoding="utf-8"))
OUT = BASE / "panel.html"
OUT_TXT = BASE / "gateways.txt"

HTML = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Шлюзы и прокладки — Панель</title>
<style>
:root{
  --bg:#0e1319; --bg2:#151c25; --card:#1a232e; --card2:#212c39;
  --line:#2b3846; --text:#e8edf3; --muted:#8fa1b3;
  --accent:#e74c3c; --accent2:#ff7a5c; --green:#2ecc71; --amber:#f1c40f;
  --radius:14px; --shadow:0 8px 24px rgba(0,0,0,.35);
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font:15px/1.45 "Segoe UI",system-ui,-apple-system,sans-serif;min-height:100vh}
a{color:var(--accent2);text-decoration:none}
button{font:inherit;cursor:pointer}
.topbar{position:sticky;top:0;z-index:50;display:flex;align-items:center;gap:16px;
  padding:14px 24px;background:linear-gradient(135deg,#1a232e 0%,#151c25 60%);
  border-bottom:1px solid var(--line);flex-wrap:wrap}
.logo{display:flex;align-items:center;gap:10px;font-weight:700;font-size:18px}
.logo .mark{width:34px;height:34px;border-radius:10px;display:grid;place-items:center;
  background:linear-gradient(135deg,var(--accent),var(--accent2));font-size:17px}
.stats{margin-left:auto;display:flex;gap:8px;flex-wrap:wrap}
.stat{display:flex;align-items:center;gap:7px;background:var(--card);border:1px solid var(--line);
  border-radius:999px;padding:6px 13px;font-size:13px;color:var(--muted)}
.stat b{color:var(--text)}
main{max-width:1280px;margin:0 auto;padding:18px 24px 80px}
.toolbar{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px;align-items:center}
input{background:var(--bg2);border:1px solid var(--line);color:var(--text);
  border-radius:10px;padding:10px 14px;font:inherit;outline:none;transition:.15s;flex:1;min-width:220px}
input:focus{border-color:var(--accent)}
.btn{background:linear-gradient(135deg,var(--accent),var(--accent2));border:none;color:#fff;
  border-radius:10px;padding:10px 16px;font-weight:700;transition:.15s}
.btn:hover{filter:brightness(1.1)}
.btn.ghost{background:var(--card2);color:var(--text);border:1px solid var(--line)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  padding:16px 18px;display:flex;flex-direction:column;gap:10px;transition:.18s}
.card:hover{border-color:var(--accent)}
.head{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.head h3{font-size:17px}
.head .dom{color:var(--muted);font-size:13px}
.type{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;
  border-radius:999px;padding:3px 11px;font-size:12px;font-weight:700}
.fee{background:var(--bg2);border:1px solid var(--line);border-radius:8px;
  padding:6px 10px;font-size:12.5px;color:var(--muted)}
details{background:var(--bg2);border:1px solid var(--line);border-radius:10px;padding:9px 12px}
details summary{cursor:pointer;font-weight:700;font-size:13.5px;color:var(--accent2);user-select:none}
details[open] summary{margin-bottom:8px}
.kv{display:grid;grid-template-columns:110px 1fr;gap:5px 12px;font-size:13px;margin-top:6px}
.kv .k{color:var(--muted)}
.kv .v{font-weight:600}
ul.lv{list-style:none;margin-top:6px}
ul.lv li{padding:3px 0 3px 18px;position:relative;font-size:13px}
ul.lv li::before{content:"▸";position:absolute;left:2px;color:var(--accent2)}
.note{font-size:12.5px;color:var(--amber)}

/* --- раскрывающаяся менюшка прокладок --- */
.ptoggle{display:flex;align-items:center;justify-content:space-between;gap:8px;
  background:linear-gradient(135deg,#1f2a37,#1a232e);border:1px solid var(--line);
  border-radius:10px;padding:10px 13px;font-weight:700;font-size:13.5px;cursor:pointer;
  user-select:none;transition:.15s}
.ptoggle:hover{border-color:var(--accent2)}
.ptoggle .arr{transition:.2s;color:var(--accent2)}
.ptoggle.on .arr{transform:rotate(90deg)}
.ptoggle b{color:var(--accent2)}
.plist{display:none;flex-direction:column;gap:8px;background:var(--bg2);
  border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin-top:-2px}
.plist.open{display:flex}
.pgroup{display:flex;flex-direction:column;gap:3px}
.pgroup-h{font-size:11.5px;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);
  border-bottom:1px dashed var(--line);padding-bottom:3px;margin-bottom:2px}
.prow{display:flex;gap:8px;align-items:baseline;font-size:13px;padding:2px 0;flex-wrap:wrap}
.prow a{font-weight:600;color:var(--text)}
.prow a:hover{color:var(--accent2)}
.prow .purl{color:var(--muted);font-size:12px;word-break:break-all}
.prow .note{font-size:11.5px}
.prow.hit{background:rgba(46,204,113,.08);border-radius:6px;padding:2px 4px}
.pcount{font-size:11.5px;color:var(--muted)}
.hint{color:var(--muted);font-size:12.5px;margin-top:16px;border-top:1px solid var(--line);padding-top:10px}
.empty{grid-column:1/-1;text-align:center;color:var(--muted);padding:60px 0}
</style>
</head>
<body>
<div class="topbar">
  <div class="logo"><span class="mark">🔌</span> Шлюзы и прокладки</div>
  <div class="stats">
    <span class="stat">Платёжек <b id="st-gw">0</b></span>
    <span class="stat">Прокладок <b id="st-p">0</b></span>
  </div>
</div>
<main>
  <div class="toolbar">
    <input type="text" id="q" placeholder="🔍 Ищи платёжку или прокладку: wert, moonpay, metamask, bitcoinhyper...">
    <button class="btn ghost" id="btn-all" onclick="toggleAll()">📂 Раскрыть все менюшки</button>
  </div>
  <div class="grid" id="grid"></div>
  <div class="hint">Кликни «📂 Все прокладки» у платёжки — раскроется полный список кошельков и сайтов, где она встроена. Данные: data.json. Обновить: <b>python3 build_panel.py</b>.</div>
</main>
<script>
const DATA = __DATA__;
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const TYPES = { "кошелёк":"👛","биржа":"🏦","NFT":"🖼","DeFi":"🔁","платёжная система":"💳","гейминг":"🎮","метавселенная":"🌐","гейминг/NFT":"🎮","брокер":"📈","платёжный процессор":"💸","шлюз":"🔌","интеграция":"🧩","мерчанты":"🏪","сайт":"🌐" };
let allOpen = false;

function toggleAll(){
  allOpen = !allOpen;
  document.querySelectorAll(".plist").forEach(el => el.classList.toggle("open", allOpen));
  document.querySelectorAll(".ptoggle").forEach(el => el.classList.toggle("on", allOpen));
  $("btn-all").textContent = allOpen ? "📁 Свернуть все менюшки" : "📂 Раскрыть все менюшки";
}

function render(q){
  q = (q || "").trim().toLowerCase();
  const cards = Object.entries(DATA).map(([dom, g]) => {
    const hit = q && (g.name.toLowerCase().includes(q) || dom.includes(q));
    const groups = {};
    g.partners.forEach(p => { (groups[p.type] = groups[p.type] || []).push(p); });
    const glist = Object.entries(groups).map(([t, arr]) => `
      <div class="pgroup">
        <div class="pgroup-h">${TYPES[t]||"•"} ${esc(t)} — ${arr.length}</div>
        ${arr.map(p => {
          const ph = q && p.name.toLowerCase().includes(q);
          const note = p.note ? `<span class="note">— ${esc(p.note)}</span>` : "";
          const purl = (p.url||"").replace(/^https?:\/\//,"").replace(/\/$/,"");
          return `<div class="prow ${ph?"hit":""}">
            <a href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.name)}</a>
            <span class="purl">${esc(purl)}</span>${note}
          </div>`;
        }).join("")}
      </div>`).join("");
    const lv = g.kyc.уровни.map(x => `<li>${esc(x)}</li>`).join("");
    const kyc = `
      <details ${q && /kyc|верифик|лимит/.test(q) ? "open" : ""}>
        <summary>🛂 KYC: ${esc(g.kyc.обязателен)}</summary>
        <div class="kv"><div class="k">Лимиты</div><div class="v">${esc(g.kyc.лимиты)}</div></div>
        <ul class="lv">${lv}</ul>
      </details>`;
    if(!hit && q && !glist.toLowerCase().includes(q)) return null;
    return `
    <div class="card">
      <div class="head"><h3>${esc(g.name)}</h3><span class="dom">${esc(dom)}</span></div>
      <div class="head"><span class="type">${esc(g.type)}</span></div>
      <div class="fee">💸 ${esc(g.fees)}</div>
      ${kyc}
      ${g.notes?`<div class="note">📌 ${esc(g.notes)}</div>`:""}
      <div class="ptoggle" onclick="this.classList.toggle('on');this.nextElementSibling.classList.toggle('open')">
        <span>📂 ВСЕ прокладки — <b>${g.partners.length}</b></span><span class="arr">▶</span>
      </div>
      <div class="plist">
        ${glist || `<div class="pcount">Нет внешних интеграций — только собственный сервис.</div>`}
      </div>
    </div>`;
  }).filter(Boolean);
  $("grid").innerHTML = cards.length ? cards.join("") : `<div class="empty">Ничего не найдено 🤷</div>`;
  $("st-gw").textContent = Object.keys(DATA).length;
  $("st-p").textContent = Object.values(DATA).reduce((a,g) => a + g.partners.length, 0);
  if(allOpen){
    document.querySelectorAll(".plist").forEach(el => el.classList.add("open"));
    document.querySelectorAll(".ptoggle").forEach(el => el.classList.add("on"));
  }
}
$("q").addEventListener("input", e => render(e.target.value));
render("");
</script>
</body>
</html>
"""


def generate() -> None:
    data = json.dumps(DATA, ensure_ascii=False).replace("</", "<\\/")
    OUT.write_text(HTML.replace("__DATA__", data), encoding="utf-8")

    lines = [
        "ПЛАТЁЖНЫЕ ШЛЮЗЫ: KYC + ВСЕ ПРОКЛАДКИ (ГДЕ ВСТРОЕН)",
        "=" * 64, "",
    ]
    for dom, g in DATA.items():
        lines += [
            f"### {g['name']} — {dom}",
            f"Тип: {g['type']}",
            f"Комиссии: {g['fees']}",
            f"KYC: {g['kyc']['обязателен']}",
            f"Лимиты: {g['kyc']['лимиты']}",
        ]
        for u in g["kyc"]["уровни"]:
            lines.append(f"  - {u}")
        if g.get("notes"):
            lines.append(f"Примечание: {g['notes']}")
        lines += ["", f"Прокладки ({len(g['partners'])}):", ""]
        by_type = {}
        for p in g["partners"]:
            by_type.setdefault(p["type"], []).append(p)
        for t, arr in by_type.items():
            lines.append(f"  [{t}]")
            for p in arr:
                note = f"  [{p['note']}]" if p.get("note") else ""
                lines.append(f"  - {p['name']} — {p['url']}{note}")
        lines += ["", "-" * 64, ""]
    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")
    n_p = sum(len(g["partners"]) for g in DATA.values())
    print(f"[i] Панель: {OUT} | gateways.txt: {len(DATA)} шлюзов, {n_p} прокладок")


if __name__ == "__main__":
    generate()
