import json
import time
import random
from datetime import datetime
from pathlib import Path

try:
from vinted_scraper import VintedScraper
SCRAPER_AVAILABLE = True
except ImportError:
SCRAPER_AVAILABLE = False
print(“vinted-scraper nao instalado”)

PRICE_DB = {
# MoonSwatch / Omega colabs
“mission to the moon swatch”: (60, 120, 180),
“moonswatch bioceramic”: (60, 120, 180),
“mission to moonphase”: (150, 280, 400),
“swatch x omega”: (80, 160, 250),
# Seiko
“seiko kinetic sportura”: (40, 90, 160),
“seiko flightmaster”: (50, 120, 200),
“seiko kinetic”: (30, 80, 130),
“seiko 7t62”: (40, 100, 170),
“seiko sna411”: (40, 100, 160),
“seiko sna413”: (40, 100, 160),
# Citizen
“citizen promaster nighthawk”: (80, 150, 220),
“citizen navihawk”: (60, 140, 220),
“citizen wingman”: (20, 60, 120),
# LIP
“lip mach 2000”: (80, 200, 350),
“montre lip mach”: (60, 180, 320),
# Yema
“yema flygraf”: (100, 250, 450),
“yema rallygraf”: (80, 200, 380),
“yema superman”: (80, 220, 400),
“yema navygraf”: (80, 200, 380),
# Swatch vintage
“swatch chrono scg”: (20, 60, 120),
“swatch irony automatic”: (25, 70, 130),
“swatch automatic”: (25, 70, 130),
# Outros
“sicura automatic”: (30, 80, 160),
“casio vintage calculator”: (15, 50, 90),
“casio dw5600”: (20, 60, 110),
“casio royale”: (20, 55, 100),
}

# IDs de categoria Vinted para relógios

# PT: verificar em vinted.pt filtrando por Acessórios > Relógios

CATALOG_IDS = {
“PT”: [“2285”],   # Relógios homem PT — confirmar no URL da Vinted PT
“FR”: [“2285”],   # Relógios homem FR — confirmar no URL da Vinted FR
}

DOMAINS = [
(“https://www.vinted.pt”, “PT”),
(“https://www.vinted.fr”, “FR”),
]

# Palavras no título que indicam que não é um relógio

JUNK_KEYWORDS = [
“capa”, “case”, “strap”, “bracelet”, “pulseira”, “correa”,
“t-shirt”, “shirt”, “poster”, “livre”, “book”, “boite”, “box only”,
“sticker”, “pin”, “lego”, “figurine”, “funko”, “pelicula”,
“perfume”, “eau de”, “cologne”,
]

def is_junk(title: str) -> bool:
t = title.lower()
return any(kw in t for kw in JUNK_KEYWORDS)

def score_deal(price, min_buy, max_buy, sell_target):
if price <= min_buy:
rating, color, score = “EXCELENTE”, “#00ff88”, 3
elif price <= max_buy:
margin = ((sell_target - price) / price) * 100
if margin >= 40:
rating, color, score = “BOM”, “#7fff7f”, 2
else:
rating, color, score = “RAZOAVEL”, “#ffd700”, 1
else:
rating, color, score = “CARO”, “#ff6666”, 0
margin_pct = round(((sell_target - price) / price) * 100, 1) if price > 0 else 0
return {“rating”: rating, “color”: color, “score”: score,
“margin_pct”: margin_pct, “sell_target”: sell_target}

def run_scan():
results = []
seen_ids = set()

```
if not SCRAPER_AVAILABLE:
    print("ERRO: vinted-scraper nao disponivel")
    return results

for base_url, domain_label in DOMAINS:
    print(f"\nVinted {domain_label}")
    catalog_ids = CATALOG_IDS.get(domain_label, [])

    try:
        scraper = VintedScraper(base_url)
    except Exception as e:
        print(f"Erro scraper {domain_label}: {e}")
        continue

    for keyword, (min_buy, max_buy, sell_target) in PRICE_DB.items():
        print(f"  Pesquisar: {keyword}")
        try:
            params = {
                "search_text": keyword,
                "order": "newest_first",
                "price_from": "5",
                "price_to": str(int(max_buy * 1.3)),
                "currency": "EUR",
            }
            # Força categoria relógios
            if catalog_ids:
                params["catalog[]"] = catalog_ids[0]

            items = scraper.search(params)
            if not items:
                time.sleep(random.uniform(1, 2))
                continue

            found = 0
            for item in items:
                try:
                    item_id = str(getattr(item, "id", "") or "")
                    uid = f"{domain_label}_{item_id}"
                    if uid in seen_ids:
                        continue
                    seen_ids.add(uid)

                    title = str(getattr(item, "title", "") or "")

                    # Filtra lixo não relacionado com relógios
                    if is_junk(title):
                        continue

                    price = float(getattr(item, "price", 0) or 0)
                    if price <= 0:
                        continue

                    deal = score_deal(price, min_buy, max_buy, sell_target)
                    if deal["score"] < 1:
                        continue

                    photo = getattr(item, "photo", "") or ""
                    if hasattr(photo, "url"):
                        photo = photo.url
                    elif isinstance(photo, dict):
                        photo = photo.get("url", "")

                    url = getattr(item, "url", "") or f"{base_url}/items/{item_id}"
                    brand = str(getattr(item, "brand_title", "") or "")

                    results.append({
                        "id": item_id,
                        "domain": domain_label,
                        "keyword": keyword,
                        "title": title,
                        "price": price,
                        "url": url,
                        "photo": str(photo),
                        "brand": brand,
                        "score": deal["score"],
                        "rating": deal["rating"],
                        "color": deal["color"],
                        "margin_pct": deal["margin_pct"],
                        "sell_target": deal["sell_target"],
                        "min_buy": min_buy,
                        "max_buy": max_buy,
                        "scanned_at": datetime.utcnow().isoformat(),
                    })
                    found += 1

                except Exception as e:
                    print(f"    item error: {e}")

            if found:
                print(f"    → {found} resultados válidos")

        except Exception as e:
            print(f"  search error '{keyword}': {e}")

        time.sleep(random.uniform(2, 4))

results.sort(key=lambda x: (x["score"], x["margin_pct"]), reverse=True)
return results
```

def generate_html(results, output_path):
now = datetime.utcnow().strftime(”%d/%m/%Y %H:%M UTC”)
total = len(results)
excellent = sum(1 for r in results if r[“score”] == 3)
good = sum(1 for r in results if r[“score”] == 2)

```
cards_html = ""
if not results:
    cards_html = '<div class="empty"><div class="empty-icon">&#8987;</div><p>Nenhum resultado encontrado neste scan.</p><p class="empty-sub">A Vinted pode estar a bloquear temporariamente. Tenta mais tarde.</p></div>'
else:
    for r in results:
        photo_html = f'<img src="{r["photo"]}" alt="" onerror="this.style.display=\'none\'">' if r["photo"] else '<div class="no-photo">&#8987;</div>'
        margin_str = f"+{r['margin_pct']}%" if r['margin_pct'] > 0 else f"{r['margin_pct']}%"
        emoji = {"EXCELENTE": "🔥", "BOM": "✅", "RAZOAVEL": "⚠️"}.get(r["rating"], "")
        cards_html += f'<a class="card score-{r["score"]}" href="{r["url"]}" target="_blank" rel="noopener"><div class="card-photo">{photo_html}</div><div class="card-body"><div class="card-badge" style="background:{r["color"]}">{emoji} {r["rating"]}</div><h3 class="card-title">{r["title"]}</h3><div class="card-meta"><span class="card-brand">{r["brand"]}</span><span class="card-domain">{r["domain"]}</span></div><div class="card-keyword">🔍 {r["keyword"]}</div><div class="card-prices"><div class="price-main">€{r["price"]:.0f}</div><div class="price-target"><span class="label">Vender ~</span><span class="value">€{r["sell_target"]:.0f}</span><span class="margin" style="color:{r["color"]}">{margin_str}</span></div></div><div class="price-range">Comprar até €{r["max_buy"]:.0f} para margem</div></div></a>'

html = f"""<!DOCTYPE html>
```

<html lang="pt">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Watch Deal Scanner</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;700&display=swap" rel="stylesheet">
<style>
:root{{--bg:#0a0a0f;--surface:#13131a;--surface2:#1c1c26;--border:#2a2a3a;--text:#e8e8f0;--text-dim:#7a7a9a;--accent:#c8a96e;--mono:'Space Mono',monospace;--sans:'DM Sans',sans-serif}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:var(--sans);min-height:100vh;background-image:radial-gradient(ellipse at 20% 0%,rgba(123,104,238,.08) 0%,transparent 50%),radial-gradient(ellipse at 80% 100%,rgba(200,169,110,.06) 0%,transparent 50%)}}
header{{border-bottom:1px solid var(--border);padding:2rem 2.5rem;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:1rem}}
.logo-mark{{font-family:var(--mono);font-size:1.6rem;font-weight:700;color:var(--accent)}}
.logo-sub{{font-size:.75rem;color:var(--text-dim);text-transform:uppercase;letter-spacing:.15em;margin-left:.75rem}}
.header-meta{{font-family:var(--mono);font-size:.7rem;color:var(--text-dim);text-align:right;line-height:1.8}}
.stats{{display:flex;gap:1px;background:var(--border);border:1px solid var(--border);border-radius:12px;overflow:hidden;margin:2rem 2.5rem}}
.stat{{flex:1;background:var(--surface);padding:1.25rem 1.5rem;text-align:center}}
.stat-val{{font-family:var(--mono);font-size:2rem;font-weight:700;margin-bottom:.35rem}}
.stat-val.fire{{color:#00ff88}}.stat-val.good{{color:#7fff7f}}.stat-val.total{{color:var(--accent)}}
.stat-label{{font-size:.7rem;color:var(--text-dim);text-transform:uppercase;letter-spacing:.12em}}
.filters{{padding:0 2.5rem 1.5rem;display:flex;gap:.5rem;flex-wrap:wrap;align-items:center}}
.filter-label{{font-size:.7rem;color:var(--text-dim);text-transform:uppercase;letter-spacing:.1em;margin-right:.5rem}}
.filter-btn{{background:var(--surface);border:1px solid var(--border);color:var(--text-dim);padding:.4rem 1rem;border-radius:999px;font-size:.78rem;cursor:pointer;font-family:var(--sans);transition:all .15s}}
.filter-btn:hover,.filter-btn.active{{border-color:var(--accent);color:var(--accent);background:rgba(200,169,110,.08)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1px;background:var(--border);border-top:1px solid var(--border);border-bottom:1px solid var(--border)}}
.card{{background:var(--surface);display:flex;flex-direction:column;text-decoration:none;color:inherit;transition:background .15s;position:relative;overflow:hidden}}
.card:hover{{background:var(--surface2)}}
.card-photo{{height:180px;overflow:hidden;background:var(--surface2);display:flex;align-items:center;justify-content:center}}
.card-photo img{{width:100%;height:100%;object-fit:cover;transition:transform .3s}}
.card:hover .card-photo img{{transform:scale(1.04)}}
.no-photo{{font-size:3rem;opacity:.2}}
.card-body{{padding:1.25rem;display:flex;flex-direction:column;gap:.6rem;flex:1}}
.card-badge{{display:inline-block;font-size:.65rem;font-weight:700;font-family:var(--mono);padding:.25rem .6rem;border-radius:4px;color:#000;align-self:flex-start}}
.card-title{{font-size:.9rem;font-weight:500;line-height:1.4}}
.card-meta{{display:flex;gap:.5rem;align-items:center}}
.card-brand{{font-size:.7rem;font-weight:600;color:var(--accent);text-transform:uppercase;letter-spacing:.08em}}
.card-domain{{font-size:.65rem;background:var(--surface2);border:1px solid var(--border);color:var(--text-dim);padding:.15rem .5rem;border-radius:4px;font-family:var(--mono)}}
.card-keyword{{font-size:.68rem;color:var(--text-dim);font-style:italic}}
.card-prices{{margin-top:auto;display:flex;align-items:baseline;gap:1rem;padding-top:.75rem;border-top:1px solid var(--border)}}
.price-main{{font-family:var(--mono);font-size:1.5rem;font-weight:700}}
.price-target{{display:flex;align-items:baseline;gap:.4rem;font-size:.78rem}}
.price-target .label{{color:var(--text-dim)}}.price-target .value{{font-family:var(--mono)}}.price-target .margin{{font-family:var(--mono);font-weight:700}}
.price-range{{font-size:.65rem;color:var(--text-dim)}}
.empty{{grid-column:1/-1;text-align:center;padding:5rem 2rem;background:var(--surface)}}
.empty-icon{{font-size:3rem;margin-bottom:1rem;opacity:.3}}
.empty-sub{{color:var(--text-dim);font-size:.85rem;margin-top:.5rem}}
footer{{padding:2rem 2.5rem;border-top:1px solid var(--border);display:flex;justify-content:space-between;font-size:.72rem;color:var(--text-dim);font-family:var(--mono);flex-wrap:wrap;gap:.5rem}}
.hidden{{display:none!important}}
</style>
</head>
<body>
<header>
  <div><span class="logo-mark">WATCH SCAN</span><span class="logo-sub">Vinted PT · FR</span></div>
  <div class="header-meta">Último scan: {now}<br>{total} resultados encontrados</div>
</header>
<div class="stats">
  <div class="stat"><div class="stat-val total">{total}</div><div class="stat-label">Total</div></div>
  <div class="stat"><div class="stat-val fire">{excellent}</div><div class="stat-label">🔥 Excelente</div></div>
  <div class="stat"><div class="stat-val good">{good}</div><div class="stat-label">✅ Bom negócio</div></div>
</div>
<div class="filters">
  <span class="filter-label">Filtrar:</span>
  <button class="filter-btn active" onclick="filterCards('all',this)">Todos</button>
  <button class="filter-btn" onclick="filterCards('3',this)">🔥 Excelente</button>
  <button class="filter-btn" onclick="filterCards('2',this)">✅ Bom</button>
  <button class="filter-btn" onclick="filterCards('1',this)">⚠️ Razoável</button>
  <button class="filter-btn" onclick="filterCards('PT',this)">Vinted PT</button>
  <button class="filter-btn" onclick="filterCards('FR',this)">Vinted FR</button>
</div>
<div class="grid" id="grid">{cards_html}</div>
<footer>
  <span>Watch Deal Scanner</span>
  <span>Preços estimados — verificar sempre antes de comprar</span>
</footer>
<script>
function filterCards(val,btn){{document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));btn.classList.add('active');document.querySelectorAll('.card').forEach(card=>{{if(val==='all'){{card.classList.remove('hidden');return}}if(val==='PT'||val==='FR'){{const d=card.querySelector('.card-domain');card.classList.toggle('hidden',!d||!d.textContent.includes(val));}}else{{card.classList.toggle('hidden',!card.classList.contains('score-'+val));}}}})}}</script>
</body></html>"""

```
Path(output_path).parent.mkdir(parents=True, exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Dashboard: {output_path}")
```

if **name** == “**main**”:
print(f”Watch Deal Scanner — {len(PRICE_DB)} keywords”)
results = run_scan()
print(f”{len(results)} oportunidades encontradas”)
generate_html(results, “docs/index.html”)
with open(“docs/results.json”, “w”, encoding=“utf-8”) as f:
json.dump(results, f, ensure_ascii=False, indent=2)
print(“Concluido!”)