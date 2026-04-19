"""
Watch Deal Scanner — Vinted PT + FR
Usa vinted-scraper para contornar bloqueios de cookie
"""

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
    print("❌ vinted-scraper não instalado — corre: pip install vinted-scraper")

# ─────────────────────────────────────────────
#  PRICE DATABASE — valor real de mercado (€)
#  Formato: "keyword": (min_buy, max_buy, sell_target)
#  min_buy = máximo que pagas para ter margem
#  sell_target = preço realista no Chrono24/eBay
# ─────────────────────────────────────────────
PRICE_DB = {
    # Swatch / MoonSwatch
    "moonswatch": (60, 120, 180),
    "bioceramic": (60, 120, 180),
    "mission to moon": (70, 130, 200),
    "cold moon": (150, 250, 350),
    "earthphase": (150, 280, 400),

    # Seiko vintage
    "seiko kinetic sportura": (40, 90, 160),
    "seiko flightmaster": (50, 120, 200),
    "seiko kinetic": (30, 80, 130),
    "seiko 7t62": (40, 100, 170),
    "seiko sna": (40, 100, 160),

    # Citizen
    "citizen promaster nighthawk": (80, 150, 220),
    "citizen wingman": (20, 60, 120),
    "citizen navihawk": (60, 140, 220),

    # LIP
    "lip mach 2000": (80, 200, 350),
    "lip mach": (60, 180, 320),
    "lip roger tallon": (100, 250, 500),
    "montre lip": (40, 120, 200),

    # Yema
    "yema flygraf": (100, 250, 450),
    "yema rallygraf": (80, 200, 380),
    "yema superman": (80, 220, 400),
    "yema": (40, 120, 220),

    # Garél
    "garel": (20, 60, 120),
    "garé": (20, 60, 120),

    # Sicura / Breitling sub
    "sicura": (30, 80, 160),

    # Casio vintage
    "casio vintage": (15, 50, 90),
    "casio ana-digi": (20, 60, 110),
    "casio aw": (15, 50, 95),

    # Swatch vintage
    "swatch chrono": (20, 60, 120),
    "swatch automatic": (25, 70, 130),
    "swatch irony": (20, 55, 100),
    "swatch musicall": (30, 80, 150),
    "swatch vintage": (15, 50, 100),
}

# Domínios a pesquisar
DOMAINS = [
    ("https://www.vinted.pt", "PT"),
    ("https://www.vinted.fr", "FR"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8",
    "Referer": "https://www.vinted.pt/",
}


def get_cookie(base_url: str) -> str | None:
    """Obtém cookie de sessão da Vinted."""
    try:
        req = urllib.request.Request(base_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            cookies = resp.headers.get("Set-Cookie", "")
            for part in cookies.split(";"):
                part = part.strip()
                if part.startswith("access_token_web="):
                    return part
    except Exception as e:
        print(f"  [!] Cookie error for {base_url}: {e}")
    return None


def search_vinted(base_url: str, query: str, cookie: str | None, max_price: float) -> list[dict]:
    """Pesquisa items no Vinted."""
    params = {
        "search_text": query,
        "order": "newest_first",
        "price_to": str(int(max_price)),
        "currency": "EUR",
        "per_page": "48",
    }
    url = f"{base_url}/api/v2/catalog/items?{urllib.parse.urlencode(params)}"

    req_headers = dict(HEADERS)
    if cookie:
        req_headers["Cookie"] = cookie

    try:
        req = urllib.request.Request(url, headers=req_headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("items", [])
    except urllib.error.HTTPError as e:
        print(f"  [!] HTTP {e.code} for query '{query}' on {base_url}")
    except Exception as e:
        print(f"  [!] Error for query '{query}': {e}")
    return []


def score_deal(price: float, min_buy: float, max_buy: float, sell_target: float) -> dict:
    """Avalia qualidade do negócio."""
    if price <= min_buy:
        rating = "🔥 EXCELENTE"
        color = "#00ff88"
        score = 3
    elif price <= max_buy:
        margin = ((sell_target - price) / price) * 100
        if margin >= 40:
            rating = "✅ BOM"
            color = "#7fff7f"
            score = 2
        else:
            rating = "⚠️ RAZOÁVEL"
            color = "#ffd700"
            score = 1
    else:
        rating = "❌ CARO"
        color = "#ff6666"
        score = 0

    margin_pct = round(((sell_target - price) / price) * 100, 1) if price > 0 else 0

    return {
        "rating": rating,
        "color": color,
        "score": score,
        "margin_pct": margin_pct,
        "sell_target": sell_target,
    }


def run_scan() -> list[dict]:
    """Executa scan completo e retorna resultados."""
    results = []
    seen_ids = set()

    for base_url, domain_label in DOMAINS:
        print(f"\n📡 A pesquisar em Vinted {domain_label}...")
        cookie = get_cookie(base_url)
        if cookie:
            print(f"  ✓ Cookie obtido")
        else:
            print(f"  ⚠ Sem cookie, a tentar mesmo assim...")

        for keyword, (min_buy, max_buy, sell_target) in PRICE_DB.items():
            # Só pesquisa se houver margem potencial razoável
            print(f"  🔍 '{keyword}'")
            items = search_vinted(base_url, keyword, cookie, max_buy * 1.3)

            for item in items:
                item_id = str(item.get("id", ""))
                uid = f"{domain_label}_{item_id}"
                if uid in seen_ids:
                    continue
                seen_ids.add(uid)

                try:
                    price = float(item.get("price", {}).get("amount", 0))
                except (TypeError, ValueError):
                    try:
                        price = float(item.get("price", 0))
                    except (TypeError, ValueError):
                        continue

                if price <= 0:
                    continue

                deal = score_deal(price, min_buy, max_buy, sell_target)

                # Só inclui se tiver algum interesse (score >= 1)
                if deal["score"] < 1:
                    continue

                photo = ""
                photos = item.get("photos", [])
                if photos and isinstance(photos, list):
                    photo = photos[0].get("url", "") if isinstance(photos[0], dict) else ""

                results.append({
                    "id": item_id,
                    "domain": domain_label,
                    "keyword": keyword,
                    "title": item.get("title", "—"),
                    "price": price,
                    "url": item.get("url", f"{base_url}/items/{item_id}"),
                    "photo": photo,
                    "brand": item.get("brand_title", "—"),
                    "score": deal["score"],
                    "rating": deal["rating"],
                    "color": deal["color"],
                    "margin_pct": deal["margin_pct"],
                    "sell_target": deal["sell_target"],
                    "min_buy": min_buy,
                    "max_buy": max_buy,
                    "scanned_at": datetime.utcnow().isoformat(),
                })

            # Pausa para não bater nos rate limits
            time.sleep(random.uniform(1.5, 3.0))

    # Ordena por score desc, depois margem desc
    results.sort(key=lambda x: (x["score"], x["margin_pct"]), reverse=True)
    return results


def generate_html(results: list[dict], output_path: str) -> None:
    """Gera dashboard HTML."""
    now = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")
    total = len(results)
    excellent = sum(1 for r in results if r["score"] == 3)
    good = sum(1 for r in results if r["score"] == 2)

    cards_html = ""
    if not results:
        cards_html = """
        <div class="empty">
            <div class="empty-icon">⌚</div>
            <p>Nenhum resultado encontrado neste scan.</p>
            <p class="empty-sub">Tenta novamente mais tarde ou ajusta as keywords no script.</p>
        </div>
        """
    else:
        for r in results:
            photo_html = f'<img src="{r["photo"]}" alt="{r["title"]}" onerror="this.style.display=\'none\'">' if r["photo"] else '<div class="no-photo">⌚</div>'
            margin_str = f"+{r['margin_pct']}%" if r['margin_pct'] > 0 else f"{r['margin_pct']}%"
            cards_html += f"""
            <a class="card score-{r['score']}" href="{r['url']}" target="_blank" rel="noopener">
                <div class="card-photo">{photo_html}</div>
                <div class="card-body">
                    <div class="card-badge" style="background:{r['color']}">{r['rating']}</div>
                    <h3 class="card-title">{r['title']}</h3>
                    <div class="card-meta">
                        <span class="card-brand">{r['brand']}</span>
                        <span class="card-domain">{r['domain']}</span>
                    </div>
                    <div class="card-keyword">🔍 {r['keyword']}</div>
                    <div class="card-prices">
                        <div class="price-main">€{r['price']:.0f}</div>
                        <div class="price-target">
                            <span class="label">Vender ~</span>
                            <span class="value">€{r['sell_target']:.0f}</span>
                            <span class="margin" style="color:{r['color']}">{margin_str}</span>
                        </div>
                    </div>
                    <div class="price-range">
                        Comprar até €{r['max_buy']:.0f} para margem
                    </div>
                </div>
            </a>
            """

    html = f"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>⌚ Watch Deal Scanner</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #0a0a0f;
    --surface: #13131a;
    --surface2: #1c1c26;
    --border: #2a2a3a;
    --text: #e8e8f0;
    --text-dim: #7a7a9a;
    --accent: #c8a96e;
    --accent2: #7b68ee;
    --mono: 'Space Mono', monospace;
    --sans: 'DM Sans', sans-serif;
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    background: var(--bg);
    color: var(--text);
    font-family: var(--sans);
    min-height: 100vh;
    background-image:
      radial-gradient(ellipse at 20% 0%, rgba(123,104,238,0.08) 0%, transparent 50%),
      radial-gradient(ellipse at 80% 100%, rgba(200,169,110,0.06) 0%, transparent 50%);
  }}

  header {{
    border-bottom: 1px solid var(--border);
    padding: 2rem 2.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 1rem;
  }}

  .logo {{
    display: flex;
    align-items: baseline;
    gap: 0.75rem;
  }}

  .logo-mark {{
    font-family: var(--mono);
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--accent);
    letter-spacing: -0.02em;
  }}

  .logo-sub {{
    font-size: 0.75rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.15em;
    font-weight: 500;
  }}

  .header-meta {{
    text-align: right;
    font-family: var(--mono);
    font-size: 0.7rem;
    color: var(--text-dim);
    line-height: 1.8;
  }}

  .stats {{
    display: flex;
    gap: 1px;
    background: var(--border);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    margin: 2rem 2.5rem;
  }}

  .stat {{
    flex: 1;
    background: var(--surface);
    padding: 1.25rem 1.5rem;
    text-align: center;
  }}

  .stat-val {{
    font-family: var(--mono);
    font-size: 2rem;
    font-weight: 700;
    line-height: 1;
    margin-bottom: 0.35rem;
  }}

  .stat-val.fire {{ color: #00ff88; }}
  .stat-val.good {{ color: #7fff7f; }}
  .stat-val.total {{ color: var(--accent); }}

  .stat-label {{
    font-size: 0.7rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.12em;
  }}

  .filters {{
    padding: 0 2.5rem 1.5rem;
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    align-items: center;
  }}

  .filter-label {{
    font-size: 0.7rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-right: 0.5rem;
  }}

  .filter-btn {{
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text-dim);
    padding: 0.4rem 1rem;
    border-radius: 999px;
    font-size: 0.78rem;
    cursor: pointer;
    font-family: var(--sans);
    transition: all 0.15s;
  }}

  .filter-btn:hover, .filter-btn.active {{
    border-color: var(--accent);
    color: var(--accent);
    background: rgba(200,169,110,0.08);
  }}

  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1px;
    background: var(--border);
    border-top: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
  }}

  .card {{
    background: var(--surface);
    display: flex;
    flex-direction: column;
    text-decoration: none;
    color: inherit;
    transition: background 0.15s;
    position: relative;
    overflow: hidden;
  }}

  .card:hover {{
    background: var(--surface2);
  }}

  .card::after {{
    content: '↗';
    position: absolute;
    top: 1rem;
    right: 1rem;
    font-size: 0.9rem;
    color: var(--text-dim);
    opacity: 0;
    transition: opacity 0.15s;
  }}

  .card:hover::after {{ opacity: 1; }}

  .card-photo {{
    height: 180px;
    overflow: hidden;
    background: var(--surface2);
    display: flex;
    align-items: center;
    justify-content: center;
  }}

  .card-photo img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.3s;
  }}

  .card:hover .card-photo img {{ transform: scale(1.04); }}

  .no-photo {{
    font-size: 3rem;
    opacity: 0.2;
  }}

  .card-body {{
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    flex: 1;
  }}

  .card-badge {{
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 700;
    font-family: var(--mono);
    padding: 0.25rem 0.6rem;
    border-radius: 4px;
    color: #000;
    align-self: flex-start;
    letter-spacing: 0.05em;
  }}

  .card-title {{
    font-size: 0.9rem;
    font-weight: 500;
    line-height: 1.4;
    color: var(--text);
  }}

  .card-meta {{
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }}

  .card-brand {{
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }}

  .card-domain {{
    font-size: 0.65rem;
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--text-dim);
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    font-family: var(--mono);
  }}

  .card-keyword {{
    font-size: 0.68rem;
    color: var(--text-dim);
    font-style: italic;
  }}

  .card-prices {{
    margin-top: auto;
    display: flex;
    align-items: baseline;
    gap: 1rem;
    padding-top: 0.75rem;
    border-top: 1px solid var(--border);
  }}

  .price-main {{
    font-family: var(--mono);
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text);
  }}

  .price-target {{
    display: flex;
    align-items: baseline;
    gap: 0.4rem;
    font-size: 0.78rem;
  }}

  .price-target .label {{ color: var(--text-dim); }}
  .price-target .value {{ font-family: var(--mono); color: var(--text); }}
  .price-target .margin {{ font-family: var(--mono); font-weight: 700; }}

  .price-range {{
    font-size: 0.65rem;
    color: var(--text-dim);
  }}

  .empty {{
    grid-column: 1 / -1;
    text-align: center;
    padding: 5rem 2rem;
    background: var(--surface);
  }}

  .empty-icon {{ font-size: 3rem; margin-bottom: 1rem; opacity: 0.3; }}
  .empty-sub {{ color: var(--text-dim); font-size: 0.85rem; margin-top: 0.5rem; }}

  footer {{
    padding: 2rem 2.5rem;
    border-top: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.72rem;
    color: var(--text-dim);
    font-family: var(--mono);
    flex-wrap: wrap;
    gap: 0.5rem;
  }}

  .hidden {{ display: none !important; }}

  @media (max-width: 600px) {{
    header, .stats, .filters {{ padding-left: 1rem; padding-right: 1rem; }}
    .stats {{ margin: 1.5rem 1rem; }}
    .grid {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>

<header>
  <div class="logo">
    <span class="logo-mark">WATCH SCAN</span>
    <span class="logo-sub">Vinted PT · FR</span>
  </div>
  <div class="header-meta">
    Último scan: {now}<br>
    {total} resultados encontrados
  </div>
</header>

<div class="stats">
  <div class="stat">
    <div class="stat-val total">{total}</div>
    <div class="stat-label">Total encontrado</div>
  </div>
  <div class="stat">
    <div class="stat-val fire">{excellent}</div>
    <div class="stat-label">🔥 Excelente</div>
  </div>
  <div class="stat">
    <div class="stat-val good">{good}</div>
    <div class="stat-label">✅ Bom negócio</div>
  </div>
</div>

<div class="filters">
  <span class="filter-label">Filtrar:</span>
  <button class="filter-btn active" onclick="filterCards('all', this)">Todos</button>
  <button class="filter-btn" onclick="filterCards('3', this)">🔥 Excelente</button>
  <button class="filter-btn" onclick="filterCards('2', this)">✅ Bom</button>
  <button class="filter-btn" onclick="filterCards('1', this)">⚠️ Razoável</button>
  <button class="filter-btn" onclick="filterCards('PT', this)">Vinted PT</button>
  <button class="filter-btn" onclick="filterCards('FR', this)">Vinted FR</button>
</div>

<div class="grid" id="grid">
{cards_html}
</div>

<footer>
  <span>Watch Deal Scanner · github.com/actions</span>
  <span>Preços estimados — verificar sempre antes de comprar</span>
</footer>

<script>
function filterCards(val, btn) {{
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.card').forEach(card => {{
    if (val === 'all') {{
      card.classList.remove('hidden');
    }} else if (val === 'PT' || val === 'FR') {{
      const domain = card.querySelector('.card-domain');
      card.classList.toggle('hidden', !domain || !domain.textContent.includes(val));
    }} else {{
      card.classList.toggle('hidden', !card.classList.contains('score-' + val));
    }}
  }});
}}
</script>
</body>
</html>"""

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n✅ Dashboard gerado: {output_path}")


if __name__ == "__main__":
    print("⌚ Watch Deal Scanner iniciado...")
    print(f"   {len(PRICE_DB)} keywords · {len(DOMAINS)} domínios")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")

    results = run_scan()
    print(f"\n📊 {len(results)} oportunidades encontradas")

    generate_html(results, "docs/index.html")

    # Guarda também JSON para histórico
    with open("docs/results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("🏁 Concluído!")
