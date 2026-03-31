import json
import os
import re
import requests
from datetime import datetime, timezone, timedelta
from groq import Groq
from duckduckgo_search import DDGS

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Güvenilir Türk haber ve kampanya siteleri — sadece buralardan kabul et
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
    "ikea.com", "ciceksepeti.com",
    # Havacılık
    "thy.com", "turkishairlines.com", "pegasusairlines.com", "anadolujet.com",
    # Turizm
    "tatilsepeti.com", "etstur.com", "jolly.com.tr", "obilet.com",
    # Yemek
    "yemeksepeti.com", "getir.com",
    # Akaryakıt / Otomotiv
    "petrolofisi.com.tr", "opet.com.tr", "shell.com.tr", "bp.com.tr",
    # Haber siteleri
    "hurriyet.com.tr", "sabah.com.tr", "milliyet.com.tr",
    "ntv.com.tr", "cnnturk.com", "haberturk.com",
    "bloomberght.com", "ekonomim.com", "paraanaliz.com",
]

SEARCH_QUERIES = {
    "E-Ticaret":         "trendyol hepsiburada n11 kampanya indirim fırsat 2026",
    "Havacılık":         "thy pegasus anadolujet uçak bileti kampanya indirim fırsat 2026",
    "Yemek":             "yemeksepeti getir trendyol yemek indirim kampanya fırsat 2026",
    "Giyim & Moda":      "lcwaikiki mango zara h&m giyim kampanya indirim 2026",
    "Teknoloji":         "mediamarkt teknosa vatan samsung apple indirim kampanya 2026",
    "Sağlık & Güzellik": "watsons gratis farmasi kozmetik cilt bakım kampanya indirim 2026",
    "Ev & Yaşam":        "ikea ciceksepeti trendyol ev mobilya indirim kampanya 2026",
    "Spor":              "decathlon intersport spor malzeme indirim kampanya fırsat 2026",
    "Turizm & Otel":     "tatilsepeti etstur jolly otel tatil erken rezervasyon kampanya 2026",
    "Otomotiv":          "petrol ofisi opet shell akaryakıt araç kampanya indirim 2026",
}


def _is_trusted(url: str) -> bool:
    return any(site in url for site in TRUSTED_SITES)


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


def fetch_deal(category_name: str) -> dict | None:
    query = SEARCH_QUERIES.get(
        category_name, f"{category_name} kampanya indirim türkiye 2026"
    )

    # 1) DuckDuckGo haber araması
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

    # 2) Yeterli sonuç yoksa metin aramasıyla tamamla
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
        except Exception as e:
            print(f"  Arama hatası ({category_name}): {e}")

    if not results:
        return None

    # 3) Eski haberleri filtrele (son 5 günden eski olanları çıkar)
    recent = [r for r in results if _is_recent(r.get("date", ""), max_days=5)]
    if not recent:
        # Hiç güncel haber yoksa son 14 güne genişlet
        recent = [r for r in results if _is_recent(r.get("date", ""), max_days=14)]
    if not recent:
        print(f"  Güncel haber bulunamadı, atlandı ({category_name})")
        return None

    # 4) Güvenilir siteleri öne al
    trusted  = [r for r in recent if _is_trusted(r.get("url", ""))]
    others   = [r for r in recent if not _is_trusted(r.get("url", ""))]
    sorted_r = (trusted + others)[:6]

    # 4) En iyi 3 URL'den tam sayfa metnini çekmeyi dene
    page_content = ""
    source_url   = ""
    for r in sorted_r[:3]:
        url = r.get("url", "")
        if not url or not url.startswith("http"):
            continue
        content = _fetch_page_text(url)
        if len(content) > 300:          # Yeterli içerik
            page_content = content
            source_url   = url
            trust_tag    = "✓ güvenilir" if _is_trusted(url) else "? bilinmeyen"
            print(f"  Sayfa çekildi [{trust_tag}]: {url[:70]} ({len(content)} kar)")
            break

    # 5) Snippetler (özet)
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
