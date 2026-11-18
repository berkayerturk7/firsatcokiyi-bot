"""posted.json'dan bio link sayfasını (docs/index.html) üretir.

GitHub Pages bu klasörü https://firsatcokiyi.github.io adresinde yayınlar.
Story'lerdeki "ÜRÜN LİNKİ PROFİLDE" çağrısı bu sayfaya yönlendirir.
"""
import html
import json
from pathlib import Path

from categories import CATEGORIES, EMOJI

HERE = Path(__file__).resolve().parent
OUT = HERE / "docs" / "index.html"
MAX_ITEMS = 200


def _tl(v):
    if v is None:
        return ""
    if abs(v - round(v)) < 0.005:
        return f"{round(v):,}".replace(",", ".") + " TL"
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " TL"


AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül",
         "Ekim", "Kasım", "Aralık"]


def _found_at(it):
    """'18 Kasım 2026, 14:17' — posted_at yoksa sadece tarih."""
    stamp = it.get("posted_at") or it.get("date") or ""
    try:
        y, m, d = (int(x) for x in stamp[:10].split("-"))
    except ValueError:
        return ""
    out = f"{d} {AYLAR[m - 1]} {y}"
    if len(stamp) >= 16 and stamp[10] == "T":
        out += f", {stamp[11:16]}"
    return out


def build(posted, repo_slug):
    items = sorted(
        ({"asin": a, **v} for a, v in posted.items()),
        key=lambda it: (it.get("date", ""), it.get("posted_at", "")),
        reverse=True,
    )[:MAX_ITEMS]

    cards = []
    for it in items:
        thumb = it.get("thumb") or (
            f"https://raw.githubusercontent.com/{repo_slug}/main/{it['post_image']}"
            if it.get("post_image") else "")
        cat = it.get("category") or "Diğer"
        days = it.get("days", 365)
        url = it.get("url") or f"https://www.amazon.com.tr/dp/{it['asin']}"
        cards.append(f"""
      <article class="card" data-cat="{html.escape(cat)}" id="{it['asin']}">
        <a class="img" href="{html.escape(url)}" target="_blank" rel="noopener nofollow">
          <img src="{html.escape(thumb)}" alt="" loading="lazy">
        </a>
        <div class="body">
          <div class="meta">
            <span class="badge b{days}">{days} günün en düşüğü</span>
            <span class="cat">{EMOJI.get(cat, '')} {html.escape(cat)}</span>
          </div>
          <h2>{html.escape(it.get('title', ''))}</h2>
          <div class="price">
            <strong>{_tl(it.get('price'))}</strong>
            <span class="disc">-%{it.get('discount', '')}</span>
          </div>
          <div class="old">Önceki fiyat <s>{_tl(it.get('old_price'))}</s></div>
          <div class="found">Fırsatı paylaştığımız tarih: <b>{_found_at(it)}</b></div>
          <a class="btn" href="{html.escape(url)}" target="_blank" rel="noopener nofollow">Amazon'da gör</a>
        </div>
      </article>""")

    present = {it.get("category") or "Diğer" for it in items}
    chips = ['<button class="chip on" data-f="*">Tümü</button>'] + [
        f'<button class="chip" data-f="{html.escape(n)}">{e} {html.escape(n)}</button>'
        for n, e in CATEGORIES if n in present
    ]

    page = f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fırsat Çok İyi — Amazon fırsatları</title>
<meta name="description" content="Amazon.com.tr'de son 365 ve 90 günün en düşük fiyatına düşen ürünler.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
<style>
  :root {{ --navy:#131921; --orange:#ff9900; --red:#cc0c39; --gray:#6e737a; --line:#e8eaed; --bg:#f5f6f7; --card:#fff; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:Inter,system-ui,sans-serif; background:var(--bg); color:var(--navy); }}
  header {{ background:var(--card); border-bottom:4px solid var(--orange); padding:20px 16px 14px; position:sticky; top:0; z-index:2; }}
  .wrap {{ max-width:760px; margin:0 auto; }}
  h1 {{ font-size:20px; margin:0; font-weight:800; }}
  h1 span {{ color:var(--gray); font-weight:600; }}
  header p {{ margin:4px 0 12px; color:var(--gray); font-size:13px; }}
  .chips {{ display:flex; gap:8px; overflow-x:auto; padding-bottom:2px; scrollbar-width:none; }}
  .chip {{ flex:none; border:1.5px solid var(--line); background:var(--card); color:var(--navy); border-radius:999px; padding:7px 13px; font:600 13px Inter,sans-serif; cursor:pointer; }}
  .chip.on {{ background:var(--navy); color:#fff; border-color:var(--navy); }}
  main {{ padding:16px; }}
  .card {{ display:flex; gap:14px; background:var(--card); border-radius:16px; padding:14px; margin-bottom:12px; }}
  .img {{ flex:none; width:112px; height:112px; display:flex; align-items:center; justify-content:center; background:#fff; border-radius:10px; overflow:hidden; }}
  .img img {{ max-width:100%; max-height:100%; object-fit:contain; }}
  .body {{ min-width:0; flex:1; }}
  .meta {{ display:flex; gap:8px; align-items:center; flex-wrap:wrap; font-size:12px; }}
  .badge {{ font-weight:800; padding:3px 8px; border-radius:6px; }}
  .b365 {{ background:var(--orange); color:var(--navy); }}
  .b90 {{ background:var(--navy); color:var(--orange); }}
  .cat {{ color:var(--gray); font-weight:600; }}
  h2 {{ font-size:15px; font-weight:600; line-height:1.35; margin:8px 0 6px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }}
  .price {{ display:flex; align-items:center; gap:8px; }}
  .price strong {{ font-size:22px; font-weight:800; }}
  .disc {{ background:var(--red); color:#fff; font-weight:800; font-size:13px; padding:2px 8px; border-radius:999px; }}
  .old {{ color:var(--gray); font-size:12px; margin:4px 0 2px; }}
  .found {{ color:var(--gray); font-size:12px; margin:0 0 10px; }}
  .found b {{ color:var(--navy); font-weight:600; }}
  .btn {{ display:inline-block; background:var(--orange); color:var(--navy); font-weight:800; font-size:14px; text-decoration:none; padding:9px 16px; border-radius:999px; }}
  footer {{ color:var(--gray); font-size:12px; text-align:center; padding:8px 16px 32px; }}
  .hide {{ display:none; }}
</style>
</head>
<body>
<header><div class="wrap">
  <h1>Fırsat Çok İyi <span>· Amazon fırsatları</span></h1>
  <p>Son 365 ve 90 günün en düşük fiyatına düşen ürünler. En yeniler en üstte.</p>
  <nav class="chips">{''.join(chips)}</nav>
</div></header>
<main class="wrap">{''.join(cards)}
</main>
<footer>Fiyatlar, fırsatı paylaştığımız anda Amazon.com.tr'den alınmıştır. Amazon'da fiyat farklıysa
fırsat sona ermiş olabilir; stok ve fiyat her an değişebilir.</footer>
<script>
  document.querySelectorAll('.chip').forEach(function (b) {{
    b.addEventListener('click', function () {{
      document.querySelectorAll('.chip').forEach(function (x) {{ x.classList.remove('on'); }});
      b.classList.add('on');
      var f = b.dataset.f;
      document.querySelectorAll('.card').forEach(function (c) {{
        c.classList.toggle('hide', f !== '*' && c.dataset.cat !== f);
      }});
    }});
  }});
</script>
</body>
</html>
"""
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    (OUT.parent / ".nojekyll").touch()
    return OUT
