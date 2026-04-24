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
    print("vinted-scraper nao instalado")

try:
    from ebay_pricer import get_market_price, get_cache_stats
    EBAY_PRICER_AVAILABLE = True
except ImportError:
    EBAY_PRICER_AVAILABLE = False
    print("ebay_pricer nao disponivel - usando precos estaticos")


PRICE_DB = {
    # Swatch
    "swatch x omega":              ("swatch", 80, 160, 250),
    "swatch chrono scg":           ("swatch", 20, 60, 120),
    "swatch irony automatic":      ("swatch", 25, 70, 130),
    "swatch automatic":            ("swatch", 25, 70, 130),
    # Seiko
    "seiko kinetic sportura":      ("seiko", 40, 90, 160),
    "seiko flightmaster":          ("seiko", 50, 120, 200),
    "seiko kinetic":               ("seiko", 30, 80, 130),
    "seiko 7t62":                  ("seiko", 40, 100, 170),
    "seiko sna411":                ("seiko", 40, 100, 160),
    "seiko sna413":                ("seiko", 40, 100, 160),
    "seiko tv case":               ("seiko", 60, 150, 250),
    "seiko lord matic":            ("seiko", 40, 100, 180),
    "seiko bellmatic":             ("seiko", 50, 120, 200),
    "seiko actus":                 ("seiko", 30, 80, 150),
    "seiko seahorse":              ("seiko", 30, 80, 150),
    "seiko 6139":                  ("seiko", 50, 130, 220),
    "seiko 5 automatic":           ("seiko", 20, 60, 110),
    # Citizen
    "citizen promaster nighthawk": ("citizen", 80, 150, 220),
    "citizen navihawk":            ("citizen", 60, 140, 220),
    "citizen wingman":             ("citizen", 20, 60, 120),
    # LIP
    "lip mach 2000":               ("lip", 80, 200, 350),
    "lip mach 2000 mini":          ("lip", 60, 160, 280),
    "lip croix du sud":            ("lip", 60, 150, 260),
    # Yema
    "yema flygraf":                ("yema", 100, 250, 450),
    "yema rallygraf":              ("yema", 80, 200, 380),
    "yema superman":               ("yema", 80, 220, 400),
    "yema navygraf":               ("yema", 80, 200, 380),
    # Longines
    "longines conquest":           ("longines", 100, 250, 450),
    "longines ultra chron":        ("longines", 80, 220, 400),
    "longines admiral":            ("longines", 60, 160, 300),
    "longines flagship":           ("longines", 60, 150, 280),
    "longines 30l":                ("longines", 80, 200, 380),
    # Tissot
    "tissot pr516":                ("tissot", 60, 150, 280),
    "tissot seastar":              ("tissot", 50, 130, 240),
    "tissot navigator":            ("tissot", 80, 200, 350),
    "tissot visodate":             ("tissot", 40, 100, 180),
    "tissot sideral":              ("tissot", 60, 160, 300),
    # Garel
    "garel automatic":             ("garel", 30, 80, 150),
    "garel vintage":               ("garel", 25, 70, 130),
    # Casio
    "casio vintage calculator":    ("casio", 15, 50, 90),
    "casio dw5600":                ("casio", 20, 60, 110),
    "casio royale":                ("casio", 20, 55, 100),
    "casio databank":              ("casio", 15, 45, 85),
    "casio mtg":                   ("casio", 60, 150, 280),
    "casio edifice":               ("casio", 30, 80, 150),
    "casio oceanus":               ("casio", 80, 200, 380),
    "casio g-shock mudmaster":     ("casio", 80, 180, 320),
    "casio g-shock gulfmaster":    ("casio", 80, 180, 320),
    "casio pro trek":              ("casio", 50, 120, 220),
    "casio a500":                  ("casio", 20, 55, 100),
    "casio f91w":                  ("casio", 10, 30, 60),
    # Omega
    "omega seamaster vintage":     ("omega", 200, 500, 900),
    "omega constellation vintage": ("omega", 150, 400, 750),
    "omega dynamic":               ("omega", 100, 280, 520),
    "omega de ville vintage":      ("omega", 120, 320, 600),
    "omega geneve":                ("omega", 100, 250, 480),
    "omega automatic vintage":     ("omega", 150, 400, 750),
    # Tudor
    "tudor oysterdate":            ("tudor", 200, 500, 950),
    "tudor prince":                ("tudor", 150, 400, 800),
    "tudor ranger":                ("tudor", 300, 700, 1300),
    "tudor submariner vintage":    ("tudor", 500, 1200, 2200),
    "tudor advisor":               ("tudor", 200, 500, 950),
    # Tag Heuer
    "tag heuer formula 1 vintage": ("tag heuer", 100, 250, 450),
    "tag heuer 1000":              ("tag heuer", 150, 350, 650),
    "tag heuer 2000":              ("tag heuer", 100, 280, 520),
    "tag heuer autavia vintage":   ("tag heuer", 300, 700, 1400),
    "tag heuer carrera vintage":   ("tag heuer", 250, 600, 1200),
    "tag heuer monza vintage":     ("tag heuer", 200, 500, 950),
}


DOMAINS = [
    ("https://www.vinted.pt", "PT"),
    ("https://www.vinted.fr", "FR"),
]

JUNK_KEYWORDS = [
    "capa", "case", "strap", "bracelet", "pulseira", "correa",
    "t-shirt", "shirt", "poster", "livre", "book", "boite", "box only",
    "sticker", "pin", "lego", "figurine", "funko", "pelicula",
    "perfume", "eau de", "cologne","livre", "jeu", "manga", "comics", "polo", "pull", "sweat", "veste", "jacket", "decal", "autocollant", "miniature", "figurine", "bd",
    "waveceptor", "wave ceptor","scatola","solaire", "occhiali", "lunettes", "glasses", "verre","boite", "caixa", "box", "etui", "case vide","chaussure",
]


def is_junk(title):
    t = title.lower()
    return any(kw in t for kw in JUNK_KEYWORDS)


def score_deal(price, min_buy, max_buy, sell_target):
    if price <= min_buy:
        rating, color, score = "EXCELENTE", "#00ff88", 3
    elif price <= max_buy:
        margin = ((sell_target - price) / price) * 100
        if margin >= 40:
            rating, color, score = "BOM", "#7fff7f", 2
        else:
            rating, color, score = "RAZOAVEL", "#ffd700", 1
    else:
        rating, color, score = "CARO", "#ff6666", 0
    margin_pct = round(((sell_target - price) / price) * 100, 1) if price > 0 else 0
    return {"rating": rating, "color": color, "score": score,
            "margin_pct": margin_pct, "sell_target": sell_target}


def run_scan():
    results = []
    seen_ids = set()

    if not SCRAPER_AVAILABLE:
        print("ERRO: vinted-scraper nao disponivel")
        return results

    # ── Print eBay cache coverage at start of scan ─────────────────────────────
    if EBAY_PRICER_AVAILABLE:
        stats = get_cache_stats(PRICE_DB)
        print(
            f"[eBay pricer] Cache: {stats['cached_fresh']}/{stats['total_keywords']} "
            f"keywords ({stats['coverage_pct']}% cobertura)"
        )

    for base_url, domain_label in DOMAINS:
        print("Vinted " + domain_label)
        try:
            scraper = VintedScraper(base_url)
        except Exception as e:
            print("Erro scraper " + domain_label + ": " + str(e))
            continue

        for keyword, (brand, min_buy, max_buy, static_sell_target) in PRICE_DB.items():
            print("  [" + brand + "] " + keyword)

            # ── Resolve sell_target: eBay live price or static fallback ────────
            if EBAY_PRICER_AVAILABLE:
                sell_target, price_source = get_market_price(keyword, fallback=static_sell_target)
                if sell_target is None:
                    sell_target = static_sell_target
                    price_source = "fallback"
            else:
                sell_target = static_sell_target
                price_source = "static"

            # ── Adjust buy thresholds proportionally if eBay price differs ────
            # Keep the same margin ratios as the static PRICE_DB
            if price_source in ("ebay", "cache") and static_sell_target > 0:
                ratio = sell_target / static_sell_target
                adj_min_buy = round(min_buy * ratio, 0)
                adj_max_buy = round(max_buy * ratio, 0)
            else:
                adj_min_buy = min_buy
                adj_max_buy = max_buy

            try:
                params = {
                    "search_text": keyword,
                    "order": "newest_first",
                    "price_from": "5",
                    "price_to": str(int(adj_max_buy * 1.3)),
                    "currency": "EUR",
                    "catalog[]": "97",
                }

                items = scraper.search(params)
                if not items:
                    time.sleep(random.uniform(1, 2))
                    continue

                found = 0
                for item in items:
                    try:
                        item_id = str(getattr(item, "id", "") or "")
                        uid = domain_label + "_" + item_id
                        if uid in seen_ids:
                            continue
                        seen_ids.add(uid)

                        title = str(getattr(item, "title", "") or "")
                        item_brand = str(getattr(item, "brand_title", "") or "").lower()

                        if item_brand and brand not in item_brand:
                            continue

                        if is_junk(title):
                            continue

                        price = float(getattr(item, "price", 0) or 0)
                        if price <= 0:
                            continue

                        deal = score_deal(price, adj_min_buy, adj_max_buy, sell_target)
                        if deal["score"] < 1:
                            continue

                        photo = getattr(item, "photo", "") or ""
                        if hasattr(photo, "url"):
                            photo = photo.url
                        elif isinstance(photo, dict):
                            photo = photo.get("url", "")

                        url = getattr(item, "url", "") or base_url + "/items/" + item_id

                        results.append({
                            "id": item_id,
                            "domain": domain_label,
                            "keyword": keyword,
                            "title": title,
                            "price": price,
                            "url": url,
                            "photo": str(photo),
                            "brand": item_brand or brand,
                            "score": deal["score"],
                            "rating": deal["rating"],
                            "color": deal["color"],
                            "margin_pct": deal["margin_pct"],
                            "sell_target": deal["sell_target"],
                            "min_buy": adj_min_buy,
                            "max_buy": adj_max_buy,
                            "price_source": price_source,   # NEW: shows data origin in JSON
                            "scanned_at": datetime.utcnow().isoformat(),
                        })
                        found += 1

                    except Exception as e:
                        print("    item error: " + str(e))

                if found:
                    print("    -> " + str(found) + " resultados validos")

            except Exception as e:
                print("  search error " + keyword + ": " + str(e))

            time.sleep(random.uniform(2, 4))

    results.sort(key=lambda x: (x["score"], x["margin_pct"]), reverse=True)
    return results


def generate_html(results, output_path):
    now = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")
    total = len(results)
    excellent = sum(1 for r in results if r["score"] == 3)
    good = sum(1 for r in results if r["score"] == 2)

    ebay_count = sum(1 for r in results if r.get("price_source") in ("ebay", "cache"))
    static_count = total - ebay_count

    cards_html = ""
    if not results:
        cards_html = '<div class="empty"><div class="empty-icon">&#8987;</div><p>Nenhum resultado encontrado neste scan.</p><p class="empty-sub">A Vinted pode estar a bloquear temporariamente. Tenta mais tarde.</p></div>'
    else:
        for r in results:
            if r["photo"]:
                photo_html = '<img src="' + r["photo"] + '" alt="" onerror="this.style.display=\'none\'">'
            else:
                photo_html = '<div class="no-photo">&#8987;</div>'
            if r["margin_pct"] > 0:
                margin_str = "+" + str(r["margin_pct"]) + "%"
            else:
                margin_str = str(r["margin_pct"]) + "%"
            emoji_map = {"EXCELENTE": "🔥", "BOM": "✅", "RAZOAVEL": "⚠️"}
            emoji = emoji_map.get(r["rating"], "")

            # Price source badge: live eBay vs static
            src = r.get("price_source", "static")
            if src in ("ebay", "cache"):
                src_badge = '<span class="price-src ebay">eBay live</span>'
            else:
                src_badge = '<span class="price-src static">preço est.</span>'

            cards_html += (
                '<a class="card score-' + str(r["score"]) + '" href="' + r["url"] + '" target="_blank" rel="noopener">'
                '<div class="card-photo">' + photo_html + '</div>'
                '<div class="card-body">'
                '<div class="card-badge" style="background:' + r["color"] + '">' + emoji + ' ' + r["rating"] + '</div>'
                '<h3 class="card-title">' + r["title"] + '</h3>'
                '<div class="card-meta"><span class="card-brand">' + r["brand"] + '</span><span class="card-domain">' + r["domain"] + '</span>' + src_badge + '</div>'
                '<div class="card-keyword">🔍 ' + r["keyword"] + '</div>'
                '<div class="card-prices">'
                '<div class="price-main">€' + str(int(r["price"])) + '</div>'
                '<div class="price-target"><span class="label">Vender ~</span><span class="value">€' + str(int(r["sell_target"])) + '</span><span class="margin" style="color:' + r["color"] + '">' + margin_str + '</span></div>'
                '</div>'
                '<div class="price-range">Comprar ate €' + str(int(r["max_buy"])) + ' para margem</div>'
                '</div></a>'
            )

    # Stats bar: add eBay coverage indicator
    ebay_pct = round(ebay_count / total * 100) if total else 0

    html = (
        '<!DOCTYPE html>'
        '<html lang="pt">'
        '<head>'
        '<meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        '<title>Watch Deal Scanner</title>'
        '<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;700&display=swap" rel="stylesheet">'
        '<style>'
        ':root{--bg:#0a0a0f;--surface:#13131a;--surface2:#1c1c26;--border:#2a2a3a;--text:#e8e8f0;--text-dim:#7a7a9a;--accent:#c8a96e;--mono:"Space Mono",monospace;--sans:"DM Sans",sans-serif}'
        '*{box-sizing:border-box;margin:0;padding:0}'
        'body{background:var(--bg);color:var(--text);font-family:var(--sans);min-height:100vh}'
        'header{border-bottom:1px solid var(--border);padding:2rem 2.5rem;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:1rem}'
        '.logo-mark{font-family:var(--mono);font-size:1.6rem;font-weight:700;color:var(--accent)}'
        '.logo-sub{font-size:.75rem;color:var(--text-dim);text-transform:uppercase;letter-spacing:.15em;margin-left:.75rem}'
        '.header-meta{font-family:var(--mono);font-size:.7rem;color:var(--text-dim);text-align:right;line-height:1.8}'
        '.stats{display:flex;gap:1px;background:var(--border);border:1px solid var(--border);border-radius:12px;overflow:hidden;margin:2rem 2.5rem}'
        '.stat{flex:1;background:var(--surface);padding:1.25rem 1.5rem;text-align:center}'
        '.stat-val{font-family:var(--mono);font-size:2rem;font-weight:700;margin-bottom:.35rem}'
        '.stat-val.fire{color:#00ff88}.stat-val.good{color:#7fff7f}.stat-val.total{color:var(--accent)}.stat-val.ebay{color:#4fc3f7}'
        '.stat-label{font-size:.7rem;color:var(--text-dim);text-transform:uppercase;letter-spacing:.12em}'
        '.search-bar{padding:0 2.5rem 1rem;}'
        '.search-input{width:100%;background:var(--surface);border:1px solid var(--border);color:var(--text);padding:.75rem 1.25rem;border-radius:8px;font-size:.9rem;font-family:var(--sans);outline:none;transition:border-color .15s}'
        '.search-input:focus{border-color:var(--accent)}'
        '.search-input::placeholder{color:var(--text-dim)}'
        '.filters{padding:0 2.5rem 1.5rem;display:flex;gap:.5rem;flex-wrap:wrap;align-items:center}'
        '.filter-label{font-size:.7rem;color:var(--text-dim);text-transform:uppercase;letter-spacing:.1em;margin-right:.5rem}'
        '.filter-btn{background:var(--surface);border:1px solid var(--border);color:var(--text-dim);padding:.4rem 1rem;border-radius:999px;font-size:.78rem;cursor:pointer;transition:all .15s}'
        '.filter-btn:hover,.filter-btn.active{border-color:var(--accent);color:var(--accent);background:rgba(200,169,110,.08)}'
        '.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1px;background:var(--border);border-top:1px solid var(--border);border-bottom:1px solid var(--border)}'
        '.card{background:var(--surface);display:flex;flex-direction:column;text-decoration:none;color:inherit;transition:background .15s}'
        '.card:hover{background:var(--surface2)}'
        '.card-photo{height:180px;overflow:hidden;background:var(--surface2);display:flex;align-items:center;justify-content:center}'
        '.card-photo img{width:100%;height:100%;object-fit:cover}'
        '.no-photo{font-size:3rem;opacity:.2}'
        '.card-body{padding:1.25rem;display:flex;flex-direction:column;gap:.6rem;flex:1}'
        '.card-badge{display:inline-block;font-size:.65rem;font-weight:700;font-family:var(--mono);padding:.25rem .6rem;border-radius:4px;color:#000;align-self:flex-start}'
        '.card-title{font-size:.9rem;font-weight:500;line-height:1.4}'
        '.card-meta{display:flex;gap:.5rem;align-items:center;flex-wrap:wrap}'
        '.card-brand{font-size:.7rem;font-weight:600;color:var(--accent);text-transform:uppercase;letter-spacing:.08em}'
        '.card-domain{font-size:.65rem;background:var(--surface2);border:1px solid var(--border);color:var(--text-dim);padding:.15rem .5rem;border-radius:4px;font-family:var(--mono)}'
        '.price-src{font-size:.6rem;padding:.15rem .45rem;border-radius:4px;font-family:var(--mono);font-weight:700}'
        '.price-src.ebay{background:rgba(79,195,247,.15);color:#4fc3f7;border:1px solid rgba(79,195,247,.3)}'
        '.price-src.static{background:var(--surface2);color:var(--text-dim);border:1px solid var(--border)}'
        '.card-keyword{font-size:.68rem;color:var(--text-dim);font-style:italic}'
        '.card-prices{margin-top:auto;display:flex;align-items:baseline;gap:1rem;padding-top:.75rem;border-top:1px solid var(--border)}'
        '.price-main{font-family:var(--mono);font-size:1.5rem;font-weight:700}'
        '.price-target{display:flex;align-items:baseline;gap:.4rem;font-size:.78rem}'
        '.price-target .label{color:var(--text-dim)}.price-target .value{font-family:var(--mono)}.price-target .margin{font-family:var(--mono);font-weight:700}'
        '.price-range{font-size:.65rem;color:var(--text-dim)}'
        '.empty{grid-column:1/-1;text-align:center;padding:5rem 2rem;background:var(--surface)}'
        '.empty-icon{font-size:3rem;margin-bottom:1rem;opacity:.3}'
        '.empty-sub{color:var(--text-dim);font-size:.85rem;margin-top:.5rem}'
        '.no-results{grid-column:1/-1;text-align:center;padding:3rem;color:var(--text-dim);font-family:var(--mono);font-size:.85rem}'
        '.hidden{display:none!important}'
        '</style>'
        '</head>'
        '<body>'
        '<header>'
        '<div><span class="logo-mark">WATCH SCAN</span><span class="logo-sub">Vinted PT · FR</span></div>'
        '<div class="header-meta">Ultimo scan: ' + now + '<br>' + str(total) + ' resultados encontrados</div>'
        '</header>'
        '<div class="stats">'
        '<div class="stat"><div class="stat-val total">' + str(total) + '</div><div class="stat-label">Total</div></div>'
        '<div class="stat"><div class="stat-val fire">' + str(excellent) + '</div><div class="stat-label">🔥 Excelente</div></div>'
        '<div class="stat"><div class="stat-val good">' + str(good) + '</div><div class="stat-label">✅ Bom negocio</div></div>'
        '<div class="stat"><div class="stat-val ebay">' + str(ebay_pct) + '%</div><div class="stat-label">📊 Precos eBay</div></div>'
        '</div>'
        '<div class="search-bar">'
        '<input class="search-input" type="text" id="searchInput" placeholder="Pesquisar por titulo, marca, keyword..." oninput="applyFilters()">'
        '</div>'
        '<div class="filters">'
        '<span class="filter-label">Filtrar:</span>'
        '<button class="filter-btn active" onclick="setFilter(\'all\',this)">Todos</button>'
        '<button class="filter-btn" onclick="setFilter(\'3\',this)">🔥 Excelente</button>'
        '<button class="filter-btn" onclick="setFilter(\'2\',this)">✅ Bom</button>'
        '<button class="filter-btn" onclick="setFilter(\'1\',this)">⚠️ Razoavel</button>'
        '<button class="filter-btn" onclick="setFilter(\'PT\',this)">Vinted PT</button>'
        '<button class="filter-btn" onclick="setFilter(\'FR\',this)">Vinted FR</button>'
        '</div>'
        '<div class="grid" id="grid">' + cards_html + '</div>'
        '<footer>'
        '<span>Watch Deal Scanner</span>'
        '<span>Precos estimados - verificar sempre antes de comprar</span>'
        '</footer>'
        '<script>'
        'var activeFilter = "all";'
        'function setFilter(val, btn) {'
        '  document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));'
        '  btn.classList.add("active");'
        '  activeFilter = val;'
        '  applyFilters();'
        '}'
        'function applyFilters() {'
        '  var query = document.getElementById("searchInput").value.toLowerCase();'
        '  var cards = document.querySelectorAll(".card");'
        '  var visible = 0;'
        '  cards.forEach(function(card) {'
        '    var title = (card.querySelector(".card-title") ? card.querySelector(".card-title").textContent : "").toLowerCase();'
        '    var brand = (card.querySelector(".card-brand") ? card.querySelector(".card-brand").textContent : "").toLowerCase();'
        '    var keyword = (card.querySelector(".card-keyword") ? card.querySelector(".card-keyword").textContent : "").toLowerCase();'
        '    var matchSearch = !query || title.includes(query) || brand.includes(query) || keyword.includes(query);'
        '    var matchFilter = true;'
        '    if (activeFilter === "PT" || activeFilter === "FR") {'
        '      var d = card.querySelector(".card-domain");'
        '      matchFilter = d && d.textContent.includes(activeFilter);'
        '    } else if (activeFilter !== "all") {'
        '      matchFilter = card.classList.contains("score-" + activeFilter);'
        '    }'
        '    var show = matchSearch && matchFilter;'
        '    card.classList.toggle("hidden", !show);'
        '    if (show) visible++;'
        '  });'
        '  var noRes = document.getElementById("no-results");'
        '  if (noRes) noRes.classList.toggle("hidden", visible > 0);'
        '}'
        '</script>'
        '</body></html>'
    )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("Dashboard: " + output_path)


if __name__ == "__main__":
    print("Watch Deal Scanner - " + str(len(PRICE_DB)) + " keywords")
    results = run_scan()
    print(str(len(results)) + " oportunidades encontradas")
    generate_html(results, "docs/index.html")
    with open("docs/results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("Concluido!")
