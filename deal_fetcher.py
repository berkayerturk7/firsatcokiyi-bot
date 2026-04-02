import json
import os
import re
import requests
from datetime import datetime, timezone, timedelta
from groq import Groq
from duckduckgo_search import DDGS

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Güvenilir Türk haber ve kampanya siteleri
TRUSTED_SITES = [
    # Teknoloji haberleri
    "webtekno.com", "donanimhaber.com", "technopat.net", "shiftdelete.net",
    "chip.com.tr", "hwp.com.tr", "pcworld.com.tr", "log.com.tr",
    # E-ticaret / karşılaştırma
    "akakce.com", "cimri.com", "incehesap.com",
    # Mağazalar
    "mediamarkt.com.tr", "teknosa.com", "vatanbilgisayar.com",
    "trendyol.com", "hepsiburada.com", "n11.com", "gittigidiyor.com",
    "a101.com.tr", "bim.com.tr", "migros.com.tr", "carrefoursa.com",
    "watsons.com.tr", "gratis.com", "lcw.com", "decathlon.com.tr",
    "ikea.com", "ciceksepeti.com", "morhipo.com", "boyner.com.tr",
    # Havacılık
    "thy.com", "turkishairlines.com", "pegasusairlines.com", "anadolujet.com",
    # Turizm
    "tatilsepeti.com", "etstur.com", "jolly.com.tr", "obilet.com",
    "enuygun.com", "biletall.com",
    # Yemek
    "yemeksepeti.com", "getir.com",
    # Akaryakıt / Otomotiv
    "petrolofisi.com.tr", "opet.com.tr", "shell.com.tr", "bp.com.tr",
    "otomobildunyasi.com", "otoban.com", "arabam.com",
    # Ulusal haber ajansları ve büyük gazeteler
    "aa.com.tr", "dha.com.tr", "iha.com.tr",
    "hurriyet.com.tr", "sabah.com.tr", "milliyet.com.tr", "sozcu.com.tr",
    "ntv.com.tr", "cnnturk.com", "haberturk.com", "t24.com.tr",
    "bloomberght.com", "ekonomim.com", "paraanaliz.com",
    "internethaber.com", "haberler.com", "timeturk.com",
    "aksam.com.tr", "takvim.com.tr", "posta.com.tr",
]

# Her kategori için birden fazla arama sorgusu — sırasıyla denenir
SEARCH_QUERIES = {
    "E-Ticaret": [
        "trendyol hepsiburada indirim kampanya fırsat bugün",
        "e-ticaret online alışveriş indirim kampanya türkiye",
        "hepsiburada trendyol n11 fırsat güncel",
    ],
    "Havacılık": [
        "uçak bileti kampanya indirim thy pegasus",
        "pegasus anadolujet uçuş fırsat bilet indirimi",
        "türk hava yolları ucuz bilet kampanya",
    ],
    "Yemek": [
        "yemeksepeti getir indirim kampanya kod",
        "restoran yemek siparişi indirim fırsat",
        "yemeksepeti getir trendyol yemek kampanya",
    ],
    "Giyim & Moda": [
        "lcwaikiki koton giyim indirim kampanya site:lcw.com OR site:hurriyet.com.tr OR site:sabah.com.tr",
        "giyim moda indirim kampanya türkiye site:webtekno.com OR site:haberler.com",
        "boyner morhipo giyim fırsat indirim site:boyner.com.tr OR site:morhipo.com",
    ],
    "Teknoloji": [
        "telefon laptop indirim kampanya site:mediamarkt.com.tr OR site:teknosa.com OR site:webtekno.com",
        "samsung apple indirim türkiye site:donanimhaber.com OR site:shiftdelete.net",
        "teknoloji ürün kampanya site:vatanbilgisayar.com OR site:chip.com.tr",
    ],
    "Sağlık & Güzellik": [
        "watsons gratis kozmetik indirim kampanya site:watsons.com.tr OR site:gratis.com OR site:hurriyet.com.tr",
        "cilt bakım ürün indirim site:sabah.com.tr OR site:milliyet.com.tr",
        "sağlık güzellik kampanya türkiye site:ntv.com.tr OR site:haberler.com",
    ],
    "Ev & Yaşam": [
        "ikea ev mobilya indirim kampanya site:ikea.com OR site:hurriyet.com.tr OR site:sabah.com.tr",
        "ev yaşam ürünü fırsat site:ciceksepeti.com OR site:haberler.com",
        "mobilya dekorasyon kampanya site:milliyet.com.tr OR site:ntv.com.tr",
    ],
    "Spor": [
        "decathlon spor indirim kampanya site:decathlon.com.tr OR site:hurriyet.com.tr OR site:sabah.com.tr",
        "spor malzeme fırsat türkiye site:ntv.com.tr OR site:haberler.com",
        "nike adidas spor indirim site:webtekno.com OR site:milliyet.com.tr",
    ],
    "Turizm & Otel": [
        "otel tatil indirim kampanya site:tatilsepeti.com OR site:hurriyet.com.tr OR site:sabah.com.tr",
        "tur fırsat yurt içi yurt dışı site:etstur.com OR site:enuygun.com",
        "tatil kampanya rezervasyon site:ntv.com.tr OR site:milliyet.com.tr",
    ],
    "Otomotiv": [
        "akaryakıt benzin motorin fiyat indirim",
        "opet petrol ofisi shell akaryakıt kampanya",
        "otomobil araç bakım lastik indirim kampanya",
    ],
}


TURKISH_DOMAINS = (
    ".com.tr", ".net.tr", ".org.tr", ".biz.tr", ".info.tr",
    ".gov.tr", ".edu.tr", ".gen.tr", ".web.tr", ".tv.tr",
)

def _is_trusted(url: str) -> bool:
    return any(site in url for site in TRUSTED_SITES)

def _is_turkish(url: str) -> bool:
    """URL'nin Türk domain'inden gelip gelmediğini kontrol eder."""
    return _is_trusted(url) or any(td in url for td in TURKISH_DOMAINS)


def _fetch_page_text(url: str, max_chars: int = 3500) -> str:
    """URL'deki sayfanın düz metnini çeker. HTML, script ve style temizlenir."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "tr-TR,tr;q=0.9",
        }
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        if resp.status_code != 200:
            return ""
        html = resp.text
        # Script, style, nav, footer gibi gürültülü blokları kaldır
        for tag in ("script", "style", "nav", "footer", "header", "aside", "iframe"):
            html = re.sub(
                rf"<{tag}[^>]*>.*?</{tag}>", "", html,
                flags=re.DOTALL | re.IGNORECASE
            )
        # Kalan HTML taglarını boşlukla değiştir
        text = re.sub(r"<[^>]+>", " ", html)
        # Çok sayıda boşluk/satır sonunu tek boşluğa indir
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception as e:
        print(f"  Sayfa çekilemedi ({url[:60]}): {e}")
        return ""


def _is_recent(date_str: str, max_days: int = 5) -> bool:
    """Haberin son max_days gün içinde yayınlanıp yayınlanmadığını kontrol eder."""
    if not date_str:
        return True  # Tarih bilgisi yoksa geçir (text aramasında tarih gelmez)
    try:
        # DuckDuckGo tarihleri genellikle ISO format: "2026-03-31T..."
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - dt
        return age.days <= max_days
    except Exception:
        return True  # Parse edilemiyorsa geçir


def _search_results(query: str) -> list:
    """Bir sorgu için DuckDuckGo haber + metin araması yapar."""
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.news(query, region="tr-tr", max_results=10):
                results.append({
                    "title": r.get("title", ""),
                    "body":  r.get("body", ""),
                    "url":   r.get("url", ""),
                    "date":  r.get("date", ""),
                })
    except Exception:
        pass
    if len(results) < 3:
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(query, region="tr-tr", max_results=10):
                    results.append({
                        "title": r.get("title", ""),
                        "body":  r.get("body", ""),
                        "url":   r.get("href", ""),
                        "date":  "",
                    })
        except Exception:
            pass
    return results


def fetch_deal(category_name: str) -> dict | None:
    queries = SEARCH_QUERIES.get(
        category_name,
        [f"{category_name} kampanya indirim türkiye bugün"]
    )

    # 1) Sırayla sorguları dene, yeterli güncel sonuç bulunana kadar
    all_results = []
    for query in queries:
        res = _search_results(query)
        all_results.extend(res)
        # Tekrar eden URL'leri çıkar
        seen = set()
        unique = []
        for r in all_results:
            if r["url"] not in seen:
                seen.add(r["url"])
                unique.append(r)
        all_results = unique

        # Yeterli güncel sonuç varsa dur
        recent_check = [r for r in all_results if _is_recent(r.get("date", ""), max_days=7)]
        if len(recent_check) >= 3:
            break

    if not all_results:
        return None

    # 2) Sadece Türk domainlerini kabul et — yabancı siteleri çıkar
    turkish = [r for r in all_results if _is_turkish(r.get("url", ""))]
    if not turkish:
        print(f"  Türk domain bulunamadı, atlandı ({category_name})")
        return None

    # 3) Tarih filtresi
    recent = [r for r in turkish if _is_recent(r.get("date", ""), max_days=7)]
    if not recent:
        recent = [r for r in turkish if _is_recent(r.get("date", ""), max_days=14)]
    if not recent:
        recent = turkish  # Tarihi olmayan TR sonuçları da kabul et

    # 4) Güvenilir siteleri öne al
    trusted  = [r for r in recent if _is_trusted(r.get("url", ""))]
    others   = [r for r in recent if not _is_trusted(r.get("url", ""))]
    sorted_r = (trusted + others)[:8]

    # 5) En iyi 5 Türk URL'den tam sayfa metnini çekmeyi dene
    page_content = ""
    source_url   = ""
    for r in sorted_r[:5]:
        url = r.get("url", "")
        if not url or not url.startswith("http") or not _is_turkish(url):
            continue
        content = _fetch_page_text(url)
        if len(content) > 200:
            page_content = content
            source_url   = url
            trust_tag    = "✓ güvenilir" if _is_trusted(url) else "? bilinmeyen"
            print(f"  Sayfa çekildi [{trust_tag}]: {url[:70]} ({len(content)} kar)")
            break

    # 6) Snippetler (özet) — sadece Türk domainleri
    snippets_text = "\n\n".join(
        f"[{i+1}] Başlık: {r['title']}\n"
        f"    Özet  : {r['body']}\n"
        f"    URL   : {r.get('url', '')}"
        for i, r in enumerate(sorted_r[:5])
    )

    # 6) Tam sayfa metni varsa ekle
    page_section = ""
    if page_content:
        page_section = (
            f"\n\n=== KAYNAK SAYFANIN TAM METNİ ===\n"
            f"URL: {source_url}\n\n"
            f"{page_content}\n"
            f"=== KAYNAK SAYFA SONU ===\n"
        )

    today = datetime.now().strftime("%d %B %Y")
    prompt = f"""Sen bir kampanya editörüsün. Aşağıdaki GERÇEK kaynak metinlerden \
"{category_name}" kategorisinde bir fırsat/kampanya çıkar.

KRİTİK KURALLAR — BUNLARA MUTLAKA UY:
1. SADECE aşağıdaki kaynak metinlerde açıkça yazan bilgileri kullan. Hiçbir şey uydurma.
2. Fiyat, indirim oranı: SADECE kaynakta açık rakam varsa doldur; yoksa null.
3. "kaynak_alinti" alanına kampanyayı doğrulayan kısa bir cümle veya ifadeyi kaynaktan yaz.
4. BUGÜN {today}. Eski kampanyaları (1 aydan eski tarihli) paylaşma — null döndür.
5. Spesifik bir kampanya/indirim/fırsat bulamazsan tüm yanıtı null döndür.

--- ARAMA SONUÇLARI ---
{snippets_text}
{page_section}
--- ARAMA SONU ---

SADECE geçerli JSON döndür (uygun kaynak yoksa sadece null):
{{
    "baslik": "Spesifik kampanya başlığı (kaynakta geçen bilgi, max 55 karakter)",
    "marka": "Ana marka adı (kaynakta geçen)",
    "aciklama": "Kampanya açıklaması — SADECE kaynakta yazan bilgi, tek cümle (max 90 karakter)",
    "eski_fiyat": "Eski fiyat rakamı (kaynakta açıkça varsa, yoksa null)",
    "yeni_fiyat": "Yeni fiyat rakamı (kaynakta açıkça varsa, yoksa null)",
    "indirim_orani": "İndirim yüzdesi (kaynakta açıkça varsa sadece sayı, yoksa null)",
    "kampanya_detay": "Ana avantaj — SADECE kaynakta geçen bilgi (örn: '%30 indirim', '9 TL bilet')",
    "ozellikler": [
        "Kaynakta geçen koşul/detay 1",
        "Kaynakta geçen koşul/detay 2",
        "Kaynakta geçen koşul/detay 3"
    ],
    "kaynak_alinti": "Kampanyayı doğrulayan kaynaktaki TAM cümle — kelimesi kelimesine kopyala (ZORUNLU)",
    "kaynak_url": "Kaynağın gerçek URL'si (ZORUNLU)",
    "kaynak_adi": "Kaynak site adı",
    "caption": "Instagram açıklaması (Türkçe, heyecanlı, SADECE doğrulanmış bilgiler, emoji+hashtag, URL sona, max 400 karakter)"
}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1100,
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()

        # JSON bloğunu ayıkla
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        if raw.lower() in ("null", "none", ""):
            print(f"  Güvenilir kampanya bulunamadı, atlandı ({category_name})")
            return None

        deal = json.loads(raw)

        # Kaynak URL zorunlu
        kaynak = deal.get("kaynak_url", "")
        if not kaynak or not kaynak.startswith("http"):
            print(f"  Kaynak URL eksik, atlandı ({category_name})")
            return None

        # Kaynak alıntı — varsa logla, yoksa uyar ama atmaya devam et
        alinti = deal.get("kaynak_alinti", "")
        trust_tag = "✓ güvenilir" if _is_trusted(kaynak) else "? bilinmeyen"
        if alinti and len(str(alinti)) >= 10:
            print(f"  [{trust_tag}] Alıntı: {str(alinti)[:80]}")
        else:
            print(f"  [{trust_tag}] Alıntı yok — kaynak URL ile devam ediliyor")

        return deal

    except Exception as e:
        print(f"  Groq hatası ({category_name}): {e}")
        return None
