"""Amazon.com.tr "365/90 günün en düşük fiyatı" rozetli fırsatları toplar ve
günün paylaşımlarını seçer.

Tarama mantığı ~/Desktop/amazon/tracker.py ile aynı: Amazon fırsat sayfası her
filtre (bubble) için ilk 30 ürünü sayfa HTML'ine JSON olarak gömüyor.
"""
import json
import random
import sys
import time
import urllib.request

BASE = "https://www.amazon.com.tr/deals?bubble-id="
BADGES = {"365 günün en düşük fiyatı": 365, "90 günün en düşük fiyatı": 90}

# Önce doğrudan rozet filtreleri, sonra çeşitlilik için kategori filtreleri
BUBBLES = [
    "lowest-365",
    "lowest-90",
    "deals-collection-deals-above-1",
    "deals-collection-baby",
    "deals-collection-beauty",
    "deals-collection-books",
    "deals-collection-camera-and-photo",
    "deals-collection-cell-phones-and-accessories",
    "deals-collection-computers-and-accessories",
    "deals-collection-diy",
    "deals-collection-fashion-apparel",
    "deals-collection-fashion-bags-accessories",
    "deals-collection-fashion-kids",
    "deals-collection-fashion-luggage",
    "deals-collection-fashion-shoes",
    "deals-collection-fashion-watches",
    "deals-collection-garden",
    "deals-collection-grocery",
    "deals-collection-headphones-speakers-and-music",
    "deals-collection-health-and-personal-care",
    "deals-collection-home",
    "deals-collection-kitchen",
    "deals-collection-music",
    "deals-collection-office-products",
    "deals-collection-otomotive",
    "deals-collection-pets",
    "deals-collection-sports-and-outdoor",
    "deals-collection-televisions",
    "deals-collection-toys",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

MIN_DISCOUNT = 10  # Bu oranın altındaki indirimler paylaşılmaz


def _fetch(url, attempts=3):
    """Amazon ara sıra 503 döndürüyor; artan beklemeyle tekrar dener."""
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            if attempt == attempts:
                raise
            time.sleep(random.uniform(6, 12) * attempt)


def _extract_products(html):
    """Sayfadaki "productSearchResponse" JSON nesnesini süslü parantez eşleyerek çıkarır."""
    i = html.find('"productSearchResponse"')
    if i < 0:
        return []
    start = html.index("{", i)
    depth, in_str, esc = 0, False, False
    for k in range(start, len(html)):
        c = html[k]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return json.loads(html[start:k + 1]).get("products", [])
    return []


def _num(s):
    try:
        return float(str(s).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _parse(p):
    badge = p.get("dealBadge") or {}
    badge_json = json.dumps(badge, ensure_ascii=False)
    days = next((d for text, d in BADGES.items() if text in badge_json), None)
    if days is None:
        return None
    price = p.get("price") or {}
    to_pay = _num((price.get("priceToPay") or {}).get("price"))
    basis = _num((price.get("basisPrice") or {}).get("price"))
    reviews = p.get("customerReviews") or {}
    image = (p.get("image") or {}).get("hiRes") or (p.get("image") or {}).get("lowRes") or {}
    return {
        "asin": p["asin"],
        "title": (p.get("title") or "").strip(),
        "days": days,
        "brand": (p.get("brandLogo") or {}).get("altText"),
        "price": to_pay,
        "old_price": basis,
        "discount": round(100 * (1 - to_pay / basis)) if to_pay and basis else None,
        "rating": _num((reviews.get("rating") or {}).get("shortDisplayString")),
        "review_count": (reviews.get("count") or {}).get("value"),
        "image": f"{image['baseUrl']}._AC_SL1200_.{image.get('extension', 'jpg')}"
                 if image.get("baseUrl") else None,
        "condition": p.get("buyingOptionType"),
        "url": f"https://www.amazon.com.tr/dp/{p['asin']}",
        "category": None,
    }


def scan(bubbles=BUBBLES):
    """Tüm filtreleri tarar; asin -> ürün sözlüğü döndürür."""
    found = {}
    for n, b in enumerate(bubbles, 1):
        try:
            products = _extract_products(_fetch(BASE + b))
            for p in products:
                item = _parse(p)
                if item:
                    found.setdefault(item["asin"], item)
                    if b.startswith("deals-collection-") and not found[item["asin"]]["category"]:
                        found[item["asin"]]["category"] = b.removeprefix("deals-collection-")
            print(f"  [{n}/{len(bubbles)}] {b}: {len(products)} ürün")
        except Exception as e:
            print(f"  [uyarı] {b}: {e}", file=sys.stderr)
        if n < len(bubbles):
            time.sleep(random.uniform(1.5, 3.5))  # Amazon'u yormamak için
    return found


def _eligible(it, posted):
    return (
        it["asin"] not in posted
        and it.get("image")
        and it.get("price")
        and it.get("old_price")
        and (it.get("discount") or 0) >= MIN_DISCOUNT
        and it.get("condition") == "NEW"
        and len(it.get("title", "")) >= 10
    )


def _score(it):
    # İndirim oranı ana kriter; puanı yüksek ve çok değerlendirilmiş ürünler hafif öne çıkar
    rating_bonus = 0
    if it.get("rating") and it.get("review_count"):
        rating_bonus = (it["rating"] - 3.5) * min(it["review_count"], 500) / 100
    return it["discount"] + rating_bonus


def select(found, posted, count=5):
    """365 ve 90 günlükleri dönüşümlü seçer; daha önce paylaşılanları ve aynı gün
    aynı marka/kategoriden ikinci ürünü atlar."""
    pools = {
        d: sorted((it for it in found.values() if it["days"] == d and _eligible(it, posted)),
                  key=_score, reverse=True)
        for d in (365, 90)
    }
    order = [365, 90] if random.random() < 0.5 else [90, 365]
    chosen, brands, cats = [], set(), set()

    def take(pool, strict):
        for it in pool:
            if it in chosen:
                continue
            brand = (it.get("brand") or "").lower()
            if strict and ((brand and brand in brands) or (it["category"] and it["category"] in cats)):
                continue
            chosen.append(it)
            brands.add(brand)
            if it["category"]:
                cats.add(it["category"])
            return True
        return False

    for strict in (True, False):  # önce çeşitlilik kuralıyla, yetmezse gevşeterek
        i = 0
        while len(chosen) < count:
            d = order[i % 2]
            if not take(pools[d], strict) and not take(pools[order[(i + 1) % 2]], strict):
                break
            i += 1
        if len(chosen) >= count:
            break
    return chosen[:count]
