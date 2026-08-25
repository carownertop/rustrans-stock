#!/usr/bin/env python3
"""Fetch inventory sheets and rebuild index.html."""

from __future__ import annotations

import csv
import html
import io
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

SHEET_ID = "1NUPKDXd7iL0S_GgQOlmZs_sIreqyGaxTYKwAKSN_l7c"
SHEETS = {
    "stock": "На складе МСК",
    "transit": "В пути",
    "discount": "Уценка МСК",
}
ROOT = Path(__file__).resolve().parent
MSK = timezone(timedelta(hours=3))


def fetch_csv(sheet_name: str) -> list[list[str]]:
    params = urllib.parse.urlencode({"tqx": "out:csv", "sheet": sheet_name})
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?{params}"
    with urllib.request.urlopen(url, timeout=60) as resp:
        text = resp.read().decode("utf-8-sig")
    return list(csv.reader(io.StringIO(text)))


def parse_num(value: str | None) -> float:
    if value is None:
        return 0.0
    s = str(value).strip().replace("\xa0", " ").replace(" ", "").replace("₽", "")
    s = s.replace(",", ".")
    s = re.sub(r"[^\d.\-]", "", s)
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def fmt_int(n: float | int) -> str:
    return f"{int(round(n)):,}".replace(",", " ")


def fmt_money(n: float | int) -> str:
    return f"{fmt_int(n)} ₽"


def esc(value: object) -> str:
    return html.escape(str(value))


def parse_stock(rows: list[list[str]]) -> tuple[dict, list[dict]]:
    meta = {"phone": "", "site": "", "usd_rate": "", "usd_date": ""}
    for row in rows[:6]:
        if not row:
            continue
        key = row[0].strip()
        val = row[1].strip() if len(row) > 1 else ""
        if key == "Телефон":
            meta["phone"] = val
        elif key == "Наш сайт":
            meta["site"] = val
        elif key.startswith("Курс USD"):
            meta["usd_date"] = key.replace("Курс USD", "").strip()
            meta["usd_rate"] = val

    items: list[dict] = []
    for row in rows[7:]:
        if not row or not row[0].strip():
            continue
        qty = parse_num(row[2] if len(row) > 2 else "")
        price = parse_num(row[5] if len(row) > 5 else "")
        premium = parse_num(row[6] if len(row) > 6 else "")
        items.append(
            {
                "sku": row[0].strip(),
                "name": row[1].strip() if len(row) > 1 else "",
                "qty": qty,
                "per_pallet": parse_num(row[3] if len(row) > 3 else ""),
                "pallets": parse_num(row[4] if len(row) > 4 else ""),
                "price_path": price,
                "price_premium": premium,
                "total_path": qty * price,
                "status": row[7].strip() if len(row) > 7 else "",
            }
        )
    return meta, items


def parse_transit(rows: list[list[str]]) -> list[dict]:
    items: list[dict] = []
    for row in rows[1:]:
        if not row or not row[0].strip():
            continue
        qty = parse_num(row[2] if len(row) > 2 else "")
        price = parse_num(row[6] if len(row) > 6 else "")
        premium = parse_num(row[7] if len(row) > 7 else "")
        items.append(
            {
                "sku": row[0].strip(),
                "name": row[1].strip() if len(row) > 1 else "",
                "qty": qty,
                "per_pallet": parse_num(row[3] if len(row) > 3 else ""),
                "pallets": parse_num(row[4] if len(row) > 4 else ""),
                "price_path": price,
                "price_premium": premium,
                "total_path": qty * price,
                "eta": row[8].strip() if len(row) > 8 else "",
            }
        )
    return items


def parse_discount(rows: list[list[str]]) -> list[dict]:
    items: list[dict] = []
    for row in rows[1:]:
        if not row or len(row) < 2 or not row[1].strip():
            continue
        qty = parse_num(row[4] if len(row) > 4 else "")
        price = parse_num(row[5] if len(row) > 5 else "")
        if qty <= 0 and price <= 0:
            continue
        defect = row[7] if len(row) > 7 else ""
        defect = defect.replace("\r", " ").replace("\n", " ").strip()
        items.append(
            {
                "sku": row[1].strip(),
                "brand": row[2].strip() if len(row) > 2 else "",
                "name": row[3].strip() if len(row) > 3 else "",
                "qty": qty,
                "price": price,
                "total": qty * price,
                "org": row[6].strip() if len(row) > 6 else "",
                "defect": defect,
            }
        )
    return items


def sum_key(items: list[dict], key: str) -> float:
    return float(sum(item[key] for item in items))


def render_stock_rows(items: list[dict]) -> str:
    rows = []
    for i, item in enumerate(items, 1):
        rows.append(
            f"""
      <tr>
        <td class="num">{i}</td>
        <td class="sku">{esc(item['sku'])}</td>
        <td class="name">{esc(item['name'])}</td>
        <td class="num">{fmt_int(item['qty'])}</td>
        <td class="num">{fmt_int(item['per_pallet'])}</td>
        <td class="num">{fmt_int(item['pallets'])}</td>
        <td class="money">{fmt_money(item['price_path'])}</td>
        <td class="money">{fmt_money(item['price_premium'])}</td>
        <td class="money total">{fmt_money(item['total_path'])}</td>
      </tr>"""
        )
    return "".join(rows)


def render_transit_rows(items: list[dict]) -> str:
    rows = []
    for i, item in enumerate(items, 1):
        rows.append(
            f"""
      <tr>
        <td class="num">{i}</td>
        <td class="sku">{esc(item['sku'])}</td>
        <td class="name">{esc(item['name'])}</td>
        <td class="num">{fmt_int(item['qty'])}</td>
        <td class="num">{fmt_int(item['per_pallet'])}</td>
        <td class="num">{fmt_int(item['pallets'])}</td>
        <td class="money">{fmt_money(item['price_path'])}</td>
        <td class="money">{fmt_money(item['price_premium'])}</td>
        <td class="money total">{fmt_money(item['total_path'])}</td>
        <td class="date">{esc(item.get('eta', ''))}</td>
      </tr>"""
        )
    return "".join(rows)


def render_discount_rows(items: list[dict]) -> str:
    rows = []
    for i, item in enumerate(items, 1):
        rows.append(
            f"""
      <tr>
        <td class="num">{i}</td>
        <td class="sku">{esc(item['sku'])}</td>
        <td class="col-brand">{esc(item['brand'])}</td>
        <td class="name">{esc(item['name'])}</td>
        <td class="num">{fmt_int(item['qty'])}</td>
        <td class="money">{fmt_money(item['price'])}</td>
        <td class="money total">{fmt_money(item['total'])}</td>
        <td class="defect">{esc(item['defect'])}</td>
      </tr>"""
        )
    return "".join(rows)


def render_html(data: dict) -> str:
    ts = data["totals"]
    meta = data["meta"]
    avg_discount = (
        ts["discount"]["total"] / ts["discount"]["qty"] if ts["discount"]["qty"] else 0
    )
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Наличие · Rustrans-Logistic</title>
  <link rel="icon" href="/rustrans-stock/favicon.svg" type="image/svg+xml" />
  <link rel="icon" href="/rustrans-stock/favicon-32.png" type="image/png" sizes="32x32" />
  <link rel="apple-touch-icon" href="/rustrans-stock/apple-touch-icon.png" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
  <style>
    :root {{
      --navy: #0b1c33;
      --navy-2: #132744;
      --ink: #152238;
      --muted: #5b6b7c;
      --line: #d9e0ea;
      --paper: #f3f6fa;
      --white: #ffffff;
      --red: #e30613;
      --red-deep: #b80510;
      --gold: #f5c518;
      --shadow: 0 18px 50px rgba(11, 28, 51, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; }}
    body {{
      font-family: "Montserrat", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(1200px 500px at 10% -10%, rgba(227, 6, 19, 0.16), transparent 55%),
        radial-gradient(900px 420px at 100% 0%, rgba(19, 39, 68, 0.18), transparent 50%),
        linear-gradient(180deg, #e9eef5 0%, var(--paper) 40%, #eef2f7 100%);
      min-height: 100vh;
    }}
    .shell {{
      width: min(1280px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 64px;
    }}
    .hero {{
      position: relative;
      overflow: hidden;
      border-radius: 28px;
      background:
        linear-gradient(135deg, rgba(227,6,19,0.18), transparent 42%),
        linear-gradient(160deg, var(--navy) 0%, var(--navy-2) 55%, #1a3358 100%);
      color: var(--white);
      box-shadow: var(--shadow);
      padding: 28px 32px 30px;
      animation: rise 0.7s ease both;
    }}
    .hero::after {{
      content: "";
      position: absolute;
      right: -80px;
      top: -60px;
      width: 280px;
      height: 280px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(245,197,24,0.22), transparent 70%);
      pointer-events: none;
    }}
    .hero-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      flex-wrap: wrap;
      position: relative;
      z-index: 1;
    }}
    .brand-lockup {{
      display: flex;
      align-items: center;
      background: #fff;
      border-radius: 16px;
      padding: 10px 14px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.18);
    }}
    .brand-lockup img {{
      display: block;
      height: 52px;
      width: auto;
      max-width: min(320px, 70vw);
    }}
    td.col-brand {{
      white-space: nowrap;
      font-weight: 600;
    }}
    .hero-meta {{
      text-align: right;
      font-size: 0.86rem;
      color: rgba(255,255,255,0.78);
      line-height: 1.55;
    }}
    .hero-meta b {{ color: var(--gold); font-weight: 700; }}
    .hero h1 {{
      position: relative;
      z-index: 1;
      margin: 22px 0 8px;
      font-size: clamp(1.6rem, 3vw, 2.2rem);
      font-weight: 800;
      letter-spacing: -0.02em;
    }}
    .hero p.lead {{
      position: relative;
      z-index: 1;
      margin: 0;
      max-width: 62ch;
      color: rgba(255,255,255,0.78);
      font-size: 0.98rem;
      line-height: 1.55;
    }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 14px;
      margin-top: 24px;
      position: relative;
      z-index: 1;
    }}
    .summary-card {{
      background: rgba(255,255,255,0.08);
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 18px;
      padding: 16px 18px;
      backdrop-filter: blur(8px);
      transition: transform 0.25s ease, background 0.25s ease;
    }}
    .summary-card:hover {{
      transform: translateY(-2px);
      background: rgba(255,255,255,0.12);
    }}
    .summary-card .label {{
      font-size: 0.75rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: rgba(255,255,255,0.62);
      font-weight: 600;
    }}
    .summary-card .value {{
      margin-top: 8px;
      font-size: 1.35rem;
      font-weight: 800;
      color: var(--gold);
    }}
    .summary-card .sub {{
      margin-top: 4px;
      font-size: 0.82rem;
      color: rgba(255,255,255,0.7);
    }}
    .tabs {{
      display: flex;
      gap: 8px;
      margin: 22px 0 14px;
      flex-wrap: wrap;
      animation: rise 0.75s ease 0.08s both;
    }}
    .tab {{
      appearance: none;
      border: 0;
      cursor: pointer;
      font: inherit;
      font-weight: 700;
      font-size: 0.92rem;
      padding: 12px 18px;
      border-radius: 999px;
      background: rgba(255,255,255,0.72);
      color: var(--ink);
      box-shadow: 0 8px 24px rgba(11,28,51,0.06);
      transition: background 0.2s ease, color 0.2s ease, transform 0.2s ease;
    }}
    .tab:hover {{ transform: translateY(-1px); }}
    .tab.active {{
      background: var(--red);
      color: white;
      box-shadow: 0 10px 24px rgba(227,6,19,0.28);
    }}
    .panel {{ display: none; animation: fade 0.35s ease both; }}
    .panel.active {{ display: block; }}
    .card {{
      background: var(--white);
      border-radius: 24px;
      box-shadow: var(--shadow);
      overflow: hidden;
      border: 1px solid rgba(11,28,51,0.05);
    }}
    .totals-bar {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1px;
      background: var(--line);
      border-bottom: 1px solid var(--line);
    }}
    .totals-bar .item {{
      background: #f8fafc;
      padding: 16px 18px;
    }}
    .totals-bar .label {{
      font-size: 0.72rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      font-weight: 700;
    }}
    .totals-bar .value {{
      margin-top: 6px;
      font-size: 1.12rem;
      font-weight: 800;
      color: var(--navy);
    }}
    .totals-bar .value.accent {{ color: var(--red); }}
    .table-wrap {{ overflow-x: auto; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 980px;
    }}
    th, td {{
      padding: 12px 14px;
      text-align: left;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
      font-size: 0.86rem;
    }}
    th {{
      position: sticky;
      top: 0;
      background: var(--navy);
      color: white;
      font-size: 0.72rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      font-weight: 700;
      white-space: nowrap;
    }}
    tbody tr:hover {{ background: #f7faff; }}
    td.num, td.money, td.date {{
      text-align: right;
      white-space: nowrap;
      font-variant-numeric: tabular-nums;
    }}
    th.num, th.money, th.date {{ text-align: right; }}
    td.sku {{
      font-weight: 700;
      color: var(--navy);
      white-space: nowrap;
    }}
    td.name {{
      max-width: 340px;
      line-height: 1.4;
      color: #243447;
    }}
    td.defect {{
      max-width: 220px;
      color: var(--muted);
      font-size: 0.8rem;
      line-height: 1.35;
    }}
    td.total {{
      font-weight: 800;
      color: var(--red-deep);
    }}
    tfoot td {{
      background: #f4f7fb;
      font-weight: 800;
      border-bottom: 0;
      color: var(--navy);
    }}
    .note {{
      margin-top: 14px;
      color: var(--muted);
      font-size: 0.82rem;
      line-height: 1.5;
      animation: rise 0.8s ease 0.12s both;
    }}
    @keyframes rise {{
      from {{ opacity: 0; transform: translateY(12px); }}
      to {{ opacity: 1; transform: none; }}
    }}
    @keyframes fade {{
      from {{ opacity: 0; transform: translateY(6px); }}
      to {{ opacity: 1; transform: none; }}
    }}
    @media (max-width: 900px) {{
      .summary {{ grid-template-columns: 1fr; }}
      .totals-bar {{ grid-template-columns: 1fr 1fr; }}
      .hero {{ padding: 22px; border-radius: 22px; }}
      .hero-meta {{ text-align: left; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <header class="hero">
      <div class="hero-top">
        <div class="brand-lockup">
          <img src="logo.png" alt="Rustrans-Logistic.ru — оригинальные импортные масла" width="444" height="110" />
        </div>
        <div class="hero-meta">
          Данные на <b>{esc(data['updated'])}</b><br />
          Курс USD: <b>{esc(meta.get('usd_rate') or '—')}</b><br />
          Обновление ежедневно · GitHub Pages
        </div>
      </div>
      <h1>Наличие масел</h1>
      <p class="lead">Сводка по складу МСК, товару в пути и уценке. Стоимость считается по цене «в пути» за канистру (для уценки — по цене уценки).</p>
      <div class="summary">
        <div class="summary-card">
          <div class="label">На складе МСК</div>
          <div class="value">{fmt_money(ts['stock']['total_path'])}</div>
          <div class="sub">{fmt_int(ts['stock']['count'])} поз. · {fmt_int(ts['stock']['qty'])} шт.</div>
        </div>
        <div class="summary-card">
          <div class="label">В пути</div>
          <div class="value">{fmt_money(ts['transit']['total_path'])}</div>
          <div class="sub">{fmt_int(ts['transit']['count'])} поз. · {fmt_int(ts['transit']['qty'])} шт.</div>
        </div>
        <div class="summary-card">
          <div class="label">Уценка МСК</div>
          <div class="value">{fmt_money(ts['discount']['total'])}</div>
          <div class="sub">{fmt_int(ts['discount']['count'])} поз. · {fmt_int(ts['discount']['qty'])} шт.</div>
        </div>
      </div>
    </header>

    <nav class="tabs" role="tablist" aria-label="Разделы наличия">
      <button class="tab active" data-tab="stock" type="button">На складе МСК</button>
      <button class="tab" data-tab="transit" type="button">В пути</button>
      <button class="tab" data-tab="discount" type="button">Уценка МСК</button>
    </nav>

    <section class="panel active" id="panel-stock" role="tabpanel">
      <div class="card">
        <div class="totals-bar">
          <div class="item"><div class="label">Позиций</div><div class="value">{fmt_int(ts['stock']['count'])}</div></div>
          <div class="item"><div class="label">Кол-во, шт</div><div class="value">{fmt_int(ts['stock']['qty'])}</div></div>
          <div class="item"><div class="label">Паллет</div><div class="value">{fmt_int(ts['stock']['pallets'])}</div></div>
          <div class="item"><div class="label">Итого по цене в пути</div><div class="value accent">{fmt_money(ts['stock']['total_path'])}</div></div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th class="num">№</th>
                <th>Артикул</th>
                <th>Номенклатура</th>
                <th class="num">Кол-во</th>
                <th class="num">В паллете</th>
                <th class="num">Паллет</th>
                <th class="money">Цена в пути</th>
                <th class="money">Цена премиум</th>
                <th class="money">Сумма в пути</th>
              </tr>
            </thead>
            <tbody>
              {render_stock_rows(data['stock'])}
            </tbody>
            <tfoot>
              <tr>
                <td colspan="3">Итого</td>
                <td class="num">{fmt_int(ts['stock']['qty'])}</td>
                <td></td>
                <td class="num">{fmt_int(ts['stock']['pallets'])}</td>
                <td></td>
                <td></td>
                <td class="money">{fmt_money(ts['stock']['total_path'])}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </section>

    <section class="panel" id="panel-transit" role="tabpanel">
      <div class="card">
        <div class="totals-bar">
          <div class="item"><div class="label">Позиций</div><div class="value">{fmt_int(ts['transit']['count'])}</div></div>
          <div class="item"><div class="label">Кол-во, шт</div><div class="value">{fmt_int(ts['transit']['qty'])}</div></div>
          <div class="item"><div class="label">Паллет</div><div class="value">{fmt_int(ts['transit']['pallets'])}</div></div>
          <div class="item"><div class="label">Итого по цене в пути</div><div class="value accent">{fmt_money(ts['transit']['total_path'])}</div></div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th class="num">№</th>
                <th>Артикул</th>
                <th>Номенклатура</th>
                <th class="num">Кол-во</th>
                <th class="num">В паллете</th>
                <th class="num">Паллет</th>
                <th class="money">Цена в пути</th>
                <th class="money">Цена премиум</th>
                <th class="money">Сумма в пути</th>
                <th class="date">Приход</th>
              </tr>
            </thead>
            <tbody>
              {render_transit_rows(data['transit'])}
            </tbody>
            <tfoot>
              <tr>
                <td colspan="3">Итого</td>
                <td class="num">{fmt_int(ts['transit']['qty'])}</td>
                <td></td>
                <td class="num">{fmt_int(ts['transit']['pallets'])}</td>
                <td></td>
                <td></td>
                <td class="money">{fmt_money(ts['transit']['total_path'])}</td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </section>

    <section class="panel" id="panel-discount" role="tabpanel">
      <div class="card">
        <div class="totals-bar">
          <div class="item"><div class="label">Позиций</div><div class="value">{fmt_int(ts['discount']['count'])}</div></div>
          <div class="item"><div class="label">Кол-во, шт</div><div class="value">{fmt_int(ts['discount']['qty'])}</div></div>
          <div class="item"><div class="label">Средняя цена</div><div class="value">{fmt_money(avg_discount)}</div></div>
          <div class="item"><div class="label">Итого сумма уценки</div><div class="value accent">{fmt_money(ts['discount']['total'])}</div></div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th class="num">№</th>
                <th>Артикул</th>
                <th>Бренд</th>
                <th>Наименование</th>
                <th class="num">Кол-во</th>
                <th class="money">Цена</th>
                <th class="money">Сумма</th>
                <th>Дефект</th>
              </tr>
            </thead>
            <tbody>
              {render_discount_rows(data['discount'])}
            </tbody>
            <tfoot>
              <tr>
                <td colspan="4">Итого</td>
                <td class="num">{fmt_int(ts['discount']['qty'])}</td>
                <td></td>
                <td class="money">{fmt_money(ts['discount']['total'])}</td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </section>

    <p class="note">
      Источник: Google Sheets «Наличие масел…». Сумма по позиции = количество × цена в пути (для уценки — × цена уценки).
      Страница обновляется автоматически каждый день.
    </p>
  </div>

  <script>
    const tabs = document.querySelectorAll('.tab');
    const panels = {{
      stock: document.getElementById('panel-stock'),
      transit: document.getElementById('panel-transit'),
      discount: document.getElementById('panel-discount'),
    }};
    tabs.forEach((tab) => {{
      tab.addEventListener('click', () => {{
        tabs.forEach((t) => t.classList.remove('active'));
        tab.classList.add('active');
        Object.values(panels).forEach((p) => p.classList.remove('active'));
        panels[tab.dataset.tab].classList.add('active');
      }});
    }});
  </script>
</body>
</html>
"""


def build() -> dict:
    stock_rows = fetch_csv(SHEETS["stock"])
    transit_rows = fetch_csv(SHEETS["transit"])
    discount_rows = fetch_csv(SHEETS["discount"])

    meta, stock = parse_stock(stock_rows)
    transit = parse_transit(transit_rows)
    discount = parse_discount(discount_rows)

    updated = meta.get("usd_date") or datetime.now(MSK).strftime("%d.%m.%Y")
    data = {
        "meta": meta,
        "updated": updated,
        "stock": stock,
        "transit": transit,
        "discount": discount,
        "totals": {
            "stock": {
                "qty": sum_key(stock, "qty"),
                "pallets": sum_key(stock, "pallets"),
                "total_path": sum_key(stock, "total_path"),
                "count": len(stock),
            },
            "transit": {
                "qty": sum_key(transit, "qty"),
                "pallets": sum_key(transit, "pallets"),
                "total_path": sum_key(transit, "total_path"),
                "count": len(transit),
            },
            "discount": {
                "qty": sum_key(discount, "qty"),
                "total": sum_key(discount, "total"),
                "count": len(discount),
            },
        },
    }

    (ROOT / "index.html").write_text(render_html(data), encoding="utf-8")
    (ROOT / "data.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return data


if __name__ == "__main__":
    result = build()
    print(
        json.dumps(
            {
                "updated": result["updated"],
                "totals": result["totals"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
