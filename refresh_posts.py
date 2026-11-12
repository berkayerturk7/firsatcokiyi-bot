"""
1. Instagram'daki son postları sil
2. Yeni görselleri feed'e yükle
3. Aynı görselleri story olarak yükle (her postun kendi haber linki ile)
"""

import os
import time
import glob
import requests
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from instagram_poster import _upload_catbox

load_dotenv()

INSTAGRAM_USER_ID = os.getenv("INSTAGRAM_USER_ID")
INSTAGRAM_TOKEN   = os.getenv("INSTAGRAM_TOKEN")
GROQ_API_KEY      = os.getenv("GROQ_API_KEY")

groq = Groq(api_key=GROQ_API_KEY)

# Son test çalışmasından fırsat bilgileri + kaynak linkleri
KNOWN_DEALS = {
    "Havacılık":          {
        "baslik": "THY 159$'dan Yurt Dışı Bilet",
        "detay": "Türk Hava Yolları ile yurt dışına 159$'dan başlayan uçuş fırsatı",
        "link": "https://www.turkishairlines.com/tr-int/kampanyalar/",
    },
    "Yemek":              {
        "baslik": "Yemeksepeti'nde Online Sipariş Fırsatı",
        "detay": "Online siparişlerde özel indirim ve kampanyalar",
        "link": "https://www.yemeksepeti.com/kampanyalar",
    },
    "Giyim_ve_Moda":      {
        "baslik": "LC Waikiki %20 İndirim",
        "detay": "Seçili ürünlerde %20'ye varan indirim fırsatı",
        "link": "https://www.lcwaikiki.com/tr-TR/kampanyalar",
    },
    "Teknoloji":          {
        "baslik": "MediaMarkt'ta %10 İndirim",
        "detay": "Seçili elektronikte özel kampanya fiyatları",
        "link": "https://www.mediamarkt.com.tr/kampanyalar",
    },
    "Sağlık_ve_Güzellik": {
        "baslik": "Watsons'da %20 İndirim",
        "detay": "Kişisel bakım ve kozmetik ürünlerde %20 indirim",
        "link": "https://www.watsons.com.tr/kampanya",
    },
    "Ev_ve_Yaşam":        {
        "baslik": "IKEA'da %10 İndirim",
        "detay": "Ev mobilya ve dekorasyon ürünlerinde özel fiyatlar",
        "link": "https://www.ikea.com/tr/tr/campaigns/",
    },
    "Spor":               {
        "baslik": "Decathlon'da %10 İndirim",
        "detay": "Spor malzeme ve ekipmanlarında büyük indirim fırsatı",
        "link": "https://www.decathlon.com.tr/kampanyalar",
    },
    "Turizm_ve_Otel":     {
        "baslik": "Tatilsepeti 20. Yıl %20 İndirim",
        "detay": "20. yıl kutlaması kapsamında tüm otellerde %20 indirim",
        "link": "https://www.tatilsepeti.com/kampanyalar",
    },
    "Otomotiv":           {
        "baslik": "Shell'de %10 Akaryakıt İndirimi",
        "detay": "Seçili Shell istasyonlarında akaryakıt indirimi kampanyası",
        "link": "https://www.shell.com.tr/suruculer/shell-club-smart.html",
    },
}

CATEGORY_HASHTAGS = {
    "Havacılık":          "#ucakbileti #thy #kampanya #seyahat #fırsat #uçuş",
    "Yemek":              "#yemeksepeti #yemek #indirim #kampanya #foodie #fırsat",
    "Giyim_ve_Moda":      "#lcwaikiki #giyim #moda #indirim #kampanya #fırsat",
    "Teknoloji":          "#mediamarkt #teknoloji #elektronik #indirim #kampanya #fırsat",
    "Sağlık_ve_Güzellik": "#watsons #kozmetik #güzellik #indirim #kampanya #fırsat",
    "Ev_ve_Yaşam":        "#ikea #ev #mobilya #dekorasyon #indirim #kampanya #fırsat",
    "Spor":               "#decathlon #spor #fitness #indirim #kampanya #fırsat",
    "Turizm_ve_Otel":     "#tatilsepeti #tatil #otel #turizm #indirim #kampanya #fırsat",
    "Otomotiv":           "#shell #akaryakıt #otomotiv #kampanya #indirim #fırsat",
}

def get_recent_post_ids(count: int) -> list:
    resp = requests.get(
        f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media",
        params={"fields": "id,timestamp", "limit": count, "access_token": INSTAGRAM_TOKEN},
        timeout=15,
    )
    return resp.json().get("data", []) if resp.status_code == 200 else []

def delete_post(media_id: str) -> bool:
    resp = requests.delete(
        f"https://graph.instagram.com/v21.0/{media_id}",
        params={"access_token": INSTAGRAM_TOKEN},
        timeout=15,
    )
    return resp.status_code == 200

def post_story_with_link(image_url: str, link: str) -> bool:
    # Link sticker ile dene
    data = {
        "image_url":    image_url,
        "media_type":   "STORIES",
        "access_token": INSTAGRAM_TOKEN,
        "link_sticker": link,
    }
    resp = requests.post(
        f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media",
        data=data, timeout=30,
    )
    # Desteklenmezse linksiz dene
    if resp.status_code != 200:
        data.pop("link_sticker")
        resp = requests.post(
            f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media",
            data=data, timeout=30,
        )
    if resp.status_code != 200:
        print(f"    Story container hatası: {resp.text}")
        return False

    container_id = resp.json().get("id")
    time.sleep(5)
    pub = requests.post(
        f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media_publish",
        data={"creation_id": container_id, "access_token": INSTAGRAM_TOKEN},
        timeout=30,
    )
    return pub.status_code == 200

def get_category(filename: str) -> str:
    return Path(filename).stem.rsplit("_", 2)[0]

def generate_caption(category: str, deal: dict) -> str:
    hashtags = CATEGORY_HASHTAGS.get(category, "#indirim #kampanya #fırsat")
    prompt = f"""Kategori: {category.replace('_', ' ')}
Başlık: {deal['baslik']}
Detay: {deal['detay']}

Profesyonel, dikkat çekici Instagram açıklaması yaz. Türkçe, emoji kullan, 2-3 cümle.
Sona: {hashtags}
Sona: 🔗 Detaylar için story'mizdeki linke tıklayın!
Sadece metni döndür."""
    try:
        resp = groq.chat.completions.create(
            model="openai/gpt-oss-120b",
            reasoning_effort="low",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500, temperature=0.4,
        )
        return resp.choices[0].message.content.strip()
    except:
        return f"🔥 {deal['baslik']}\n\n{deal['detay']}\n\n{hashtags}\n\n🔗 Detaylar için story'mizdeki linke tıklayın!"

def main():
    images = sorted(glob.glob("output/*.jpg"), key=os.path.getmtime, reverse=True)[:9]
    if not images:
        print("output/ klasöründe görsel bulunamadı.")
        return

    print(f"{'='*60}")
    print(f"  {len(images)} görsel feed + story olarak paylaşılacak")
    print(f"{'='*60}\n")

    # ── 1. Eski postları sil ────────────────────────────────────
    print("► Eski postlar siliniyor...")
    for post in get_recent_post_ids(9):
        ok = delete_post(post["id"])
        print(f"  {post['id']} → {'✅ silindi' if ok else '⚠️  silinemedi'}")
        time.sleep(2)
    print()
    time.sleep(5)

    # ── 2. Feed + Story paylaş ──────────────────────────────────
    feed_ok, story_ok = 0, 0

    for i, image_path in enumerate(reversed(images), 1):
        cat   = get_category(image_path)
        deal  = KNOWN_DEALS.get(cat, {"baslik": cat.replace("_", " ") + " Fırsatı",
                                       "detay": "Bugüne özel kampanya", "link": "https://www.instagram.com/firsatcokiyi"})
        link  = deal.get("link", "https://www.instagram.com/firsatcokiyi")

        print(f"[{i}/{len(images)}] {cat.replace('_', ' ')}")
        print(f"  Story linki: {link}")

        image_url = _upload_catbox(image_path)
        if not image_url:
            print(f"  ❌ Görsel yüklenemedi\n")
            continue

        caption = generate_caption(cat, deal)

        # Feed
        cr = requests.post(
            f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media",
            data={"image_url": image_url, "caption": caption, "access_token": INSTAGRAM_TOKEN},
            timeout=30,
        )
        if cr.status_code == 200:
            time.sleep(8)
            pr = requests.post(
                f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media_publish",
                data={"creation_id": cr.json()["id"], "access_token": INSTAGRAM_TOKEN},
                timeout=30,
            )
            if pr.status_code == 200:
                feed_ok += 1
                print(f"  ✅ Feed yayınlandı!")
            else:
                print(f"  ❌ Feed: {pr.text}")
        else:
            print(f"  ❌ Feed container: {cr.text}")

        time.sleep(5)

        # Story
        if post_story_with_link(image_url, link):
            story_ok += 1
            print(f"  ✅ Story yayınlandı! (link: {link})")
        else:
            print(f"  ❌ Story başarısız")

        print()
        if i < len(images):
            print(f"  ⏳ 35 saniye bekleniyor...\n")
            time.sleep(35)

    print(f"{'='*60}")
    print(f"  Feed : {feed_ok}/{len(images)} başarılı")
    print(f"  Story: {story_ok}/{len(images)} başarılı")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
