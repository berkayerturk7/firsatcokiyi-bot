import json
import os
from groq import Groq
from duckduckgo_search import DDGS

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Haber/kampanya odaklı spesifik arama sorguları
SEARCH_QUERIES = {
    "E-Ticaret":         "trendyol hepsiburada n11 kampanya indirim 2026 site:webtekno.com OR site:shiftdelete.net OR site:technopat.net OR site:donanimhaber.com",
    "Havacılık":         "thy pegasus anadolujet uçak bileti kampanya indirim fırsat 2026",
    "Yemek":             "yemeksepeti getir trendyol yemek indirim kampanya fırsat 2026",
    "Giyim & Moda":      "lcwaikiki mango zara h&m giyim kampanya indirim 2026",
    "Teknoloji":         "mediamarkt teknosa vatan samsung apple indirim kampanya 2026",
    "Sağlık & Güzellik": "watsons gratis farmasi kozmetik cilt bakım kampanya indirim 2026",
    "Ev & Yaşam":        "ikea çiçeksepeti trendyol ev mobilya indirim kampanya 2026",
    "Spor":              "decathlon intersport spor malzeme indirim kampanya fırsat 2026",
    "Turizm & Otel":     "tatilsepeti etstur jolly otel tatil erken rezervasyon kampanya 2026",
    "Otomotiv":          "petrol ofisi opet shell akaryakıt aksesuarı araç kampanya indirim 2026",
}

def fetch_deal(category_name: str) -> dict | None:
    query = SEARCH_QUERIES.get(category_name, f"{category_name} kampanya indirim türkiye 2026")

    # Önce haber arama dene, sonra genel arama
    results = []
    try:
        with DDGS() as ddgs:
            # Haber araması — daha güncel ve spesifik sonuçlar
            for r in ddgs.news(query, region="tr-tr", max_results=5):
                results.append({
                    "title": r.get("title", ""),
                    "body":  r.get("body", ""),
                    "href":  r.get("url", ""),
                    "date":  r.get("date", ""),
                })
    except Exception:
        pass

    if len(results) < 3:
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(query, region="tr-tr", max_results=5):
                    results.append({
                        "title": r.get("title", ""),
                        "body":  r.get("body", ""),
                        "href":  r.get("href", ""),
                    })
        except Exception as e:
            print(f"  Arama hatası ({category_name}): {e}")

    if not results:
        return None

    results_text = "\n\n".join(
        f"Başlık: {r['title']}\nİçerik: {r['body']}\nURL: {r['href']}"
        for r in results[:6]
    )

    prompt = f"""Sen bir kampanya editörüsün. Aşağıdaki arama sonuçlarından "{category_name}" kategorisinde EN SPESİFİK ve EN SOMUT fırsatı çıkar.

Önemli: Gerçek rakamlar, gerçek markalar, gerçek koşullar kullan. Örneğin:
- "Axess kredi kartıyla MediaMarkt'ta Samsung TV'de %30 indirim"
- "THY'de yurt içi uçuşlarda Kuveyt Türk kartına 2.000 TL nakit iade"
- "Trendyol'da ilk siparişe 200 TL indirim kuponu"

Arama sonuçları:
{results_text}

SADECE geçerli JSON döndür:
{{
    "baslik": "Spesifik kampanya başlığı — marka+ürün+avantaj içersin (max 55 karakter)",
    "marka": "Ana marka adı",
    "aciklama": "Kampanyanın tam koşulu tek cümleyle (max 90 karakter)",
    "eski_fiyat": "Eski fiyat rakamı (varsa, yoksa null)",
    "yeni_fiyat": "Yeni fiyat rakamı (varsa, yoksa null)",
    "indirim_orani": "İndirim yüzdesi (varsa sadece sayı, yoksa null)",
    "kampanya_detay": "Ana kampanya avantajı (örn: '2.000 TL nakit iade', '%30 indirim', '6 taksit')",
    "ozellikler": [
        "Kampanya koşulu 1 (örn: 'Minimum 2.000 TL alışveriş şartı')",
        "Kampanya koşulu 2 (örn: 'Sadece Axess kart sahiplerine özel')",
        "Kampanya koşulu 3 (örn: '31 Mart'a kadar geçerli')"
    ],
    "kaynak_url": "Kaynak URL",
    "kaynak_adi": "Kaynak site adı",
    "caption": "Instagram açıklaması — Türkçe, heyecan verici, spesifik rakamlar kullan, emoji ekle, hashtag ekle, kaynak URL sona (max 400 karakter)"
}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=900,
            temperature=0.2,
        )
        text = response.choices[0].message.content.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
    except Exception as e:
        print(f"  Groq hatası ({category_name}): {e}")
        return None
