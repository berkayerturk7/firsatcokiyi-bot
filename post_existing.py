"""
Son üretilen görselleri Instagram'a paylaşır.
Groq ile her kategori için profesyonel caption üretir.
"""

import os
import time
import glob
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from instagram_poster import post_to_instagram

load_dotenv()

INSTAGRAM_USER_ID = os.getenv("INSTAGRAM_USER_ID")
INSTAGRAM_TOKEN   = os.getenv("INSTAGRAM_TOKEN")
IMGBB_API_KEY     = os.getenv("IMGBB_API_KEY")
GROQ_API_KEY      = os.getenv("GROQ_API_KEY")

groq = Groq(api_key=GROQ_API_KEY)

# Son test çalışmasından bilinen fırsat bilgileri
KNOWN_DEALS = {
    "Havacılık":       {"baslik": "THY 159$'dan Yurt Dışı Bilet",       "detay": "Türk Hava Yolları ile yurt dışına 159$'dan başlayan uçuş fırsatı"},
    "Yemek":           {"baslik": "Yemeksepeti'nde %100 Online Sipariş Bonus", "detay": "İlk siparişinizde %100'e varan indirim fırsatları"},
    "Teknoloji":       {"baslik": "MediaMarkt'ta Büyük İndirim",         "detay": "Seçili elektronikte özel kampanya fiyatları"},
    "Sağlık_ve_Güzellik": {"baslik": "Watsons'da %20 İndirim",          "detay": "Kişisel bakım ve kozmetik ürünlerde %20 indirim"},
    "Ev_ve_Yaşam":     {"baslik": "IKEA'da %10 İndirim",                "detay": "Ev mobilya ve dekorasyon ürünlerinde özel fiyatlar"},
    "Spor":            {"baslik": "Decathlon'da %20 İndirim",            "detay": "Spor malzeme ve ekipmanlarında büyük indirim fırsatı"},
    "Turizm_ve_Otel":  {"baslik": "Tatilsepeti 20. Yıl %20 İndirim",   "detay": "20. yıl kutlaması kapsamında tüm otellerde %20 indirim"},
    "Otomotiv":        {"baslik": "Akaryakıt ve Araç Aksesuar Fırsatı", "detay": "Seçili akaryakıt istasyonlarında özel kampanya ve indirimler"},
}

CATEGORY_HASHTAGS = {
    "Havacılık":          "#ucakbileti #thy #kampanya #havacılık #seyahat #uçuş #bilet #fırsat",
    "Yemek":              "#yemeksepeti #yemek #indirim #kampanya #restoran #foodie #sipariş #fırsat",
    "Teknoloji":          "#mediamarkt #teknoloji #elektronik #indirim #kampanya #telefon #bilgisayar #fırsat",
    "Sağlık_ve_Güzellik": "#watsons #kozmetik #güzellik #ciltbakım #indirim #kampanya #bakım #fırsat",
    "Ev_ve_Yaşam":        "#ikea #ev #mobilya #dekorasyon #indirim #kampanya #yaşam #fırsat",
    "Spor":               "#decathlon #spor #fitness #malzeme #indirim #kampanya #sağlıklıyaşam #fırsat",
    "Turizm_ve_Otel":     "#tatilsepeti #tatil #otel #turizm #indirim #kampanya #seyahat #rezervasyon",
    "Otomotiv":           "#araç #otomotiv #akaryakıt #kampanya #indirim #araba #aksesuar #fırsat",
}

def get_category_from_filename(filename: str) -> str:
    name = Path(filename).stem
    parts = name.rsplit("_", 2)
    return parts[0] if parts else name

def generate_caption(category: str, deal: dict) -> str:
    hashtags = CATEGORY_HASHTAGS.get(category, "#indirim #kampanya #fırsat #türkiye")

    prompt = f"""Kategori: {category.replace("_", " ")}
Fırsat Başlığı: {deal['baslik']}
Detay: {deal['detay']}

Bu fırsat için profesyonel, dikkat çekici bir Instagram açıklaması yaz.
- Türkçe olsun
- Emoji kullan ama abartma
- Fırsatı net ve heyecan verici anlat
- 2-3 cümle yeterli
- Sona şu hashtagleri ekle: {hashtags}
- Sona "🔗 Detaylar için biyografimizdeki linke tıklayın!" ekle
- Sadece açıklama metnini döndür, başka hiçbir şey yazma"""

    try:
        resp = groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.4,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"  Caption hatası: {e}")
        return f"🔥 {deal['baslik']}\n\n{deal['detay']}\n\n{hashtags}\n\n🔗 Detaylar için biyografimizdeki linke tıklayın!"

def main():
    # Son 8 görseli al (en yeni önce)
    images = sorted(
        glob.glob("output/*.jpg"),
        key=os.path.getmtime,
        reverse=True
    )[:8]

    if not images:
        print("output/ klasöründe görsel bulunamadı.")
        return

    print(f"{'='*60}")
    print(f"  {len(images)} görsel Instagram'a paylaşılacak")
    print(f"{'='*60}\n")

    success = 0
    for i, image_path in enumerate(reversed(images), 1):  # En eski önce paylaş
        category = get_category_from_filename(image_path)
        deal = KNOWN_DEALS.get(category, {
            "baslik": category.replace("_", " ") + " Fırsatı",
            "detay": "Bugüne özel harika kampanya ve indirim fırsatları"
        })

        print(f"[{i}/{len(images)}] {category.replace('_', ' ')} paylaşılıyor...")
        print(f"  Görsel: {image_path}")

        caption = generate_caption(category, deal)
        print(f"  Caption üretildi.")

        ok = post_to_instagram(
            image_path=image_path,
            caption=caption,
            instagram_user_id=INSTAGRAM_USER_ID,
            access_token=INSTAGRAM_TOKEN,
            imgbb_api_key=IMGBB_API_KEY,
        )

        if ok:
            success += 1
            print(f"  ✅ Paylaşıldı!\n")
        else:
            print(f"  ❌ Başarısız.\n")

        if i < len(images):
            print(f"  Sonraki post için 35 saniye bekleniyor...")
            time.sleep(35)

    print(f"{'='*60}")
    print(f"  Tamamlandı: {success}/{len(images)} post başarılı")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
