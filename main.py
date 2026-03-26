import os
import sys
import time
import schedule
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from deal_fetcher    import fetch_deal
from image_generator import create_post_image, create_story_image
from instagram_poster import post_to_instagram, _upload_catbox
import requests

# ─── Konfigürasyon ─────────────────────────────────────────────────────────────
INSTAGRAM_USER_ID = os.getenv("INSTAGRAM_USER_ID", "24422570594030577")
INSTAGRAM_TOKEN   = os.getenv("INSTAGRAM_TOKEN")
IMGBB_API_KEY     = os.getenv("IMGBB_API_KEY")
PEXELS_API_KEY    = os.getenv("PEXELS_API_KEY", "")

CATEGORIES = [
    {"name": "E-Ticaret"},
    {"name": "Havacılık"},
    {"name": "Yemek"},
    {"name": "Giyim & Moda"},
    {"name": "Teknoloji"},
    {"name": "Sağlık & Güzellik"},
    {"name": "Ev & Yaşam"},
    {"name": "Spor"},
    {"name": "Turizm & Otel"},
    {"name": "Otomotiv"},
]

POST_DELAY_SECONDS = 35  # Instagram rate limit için postlar arası bekleme


def check_env():
    missing = [k for k in ["INSTAGRAM_TOKEN", "GROQ_API_KEY", "IMGBB_API_KEY"]
               if not os.getenv(k)]
    if missing:
        print(f"HATA: Eksik env değişkenleri: {', '.join(missing)}")
        print("Lütfen .env dosyasını doldurun.")
        sys.exit(1)


def _post_story(image_url: str, link: str):
    data = {"image_url": image_url, "media_type": "STORIES",
            "access_token": INSTAGRAM_TOKEN, "link_sticker": link}
    cr = requests.post(f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media",
                       data=data, timeout=30)
    if cr.status_code != 200:
        data.pop("link_sticker")
        cr = requests.post(f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media",
                           data=data, timeout=30)
    if cr.status_code == 200:
        time.sleep(5)
        pr = requests.post(f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media_publish",
                           data={"creation_id": cr.json()["id"], "access_token": INSTAGRAM_TOKEN},
                           timeout=30)
        if pr.status_code == 200:
            print(f"  Story yayinlandi! ({link[:50]})")
        else:
            print(f"  Story yayinlama hatasi.")

def run_daily(dry_run: bool = False):
    print(f"\n{'='*60}")
    print(f"  Günlük otomasyon başladı — {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print(f"{'='*60}\n")

    success_count = 0

    for category in CATEGORIES:
        cat = category["name"]
        print(f"[{cat}] İşleniyor...")

        try:
            # 1. Fırsat bul
            deal = fetch_deal(cat)
            if not deal:
                print(f"  Fırsat bulunamadı, geçiliyor.\n")
                continue
            print(f"  Fırsat: {deal.get('baslik', '-')}")

            # 2. Görsel üret
            image_path = create_post_image(deal, category, pexels_key=PEXELS_API_KEY)

            if dry_run:
                print(f"  [DRY RUN] Post atılmadı. Görsel: {image_path}\n")
                success_count += 1
                continue

            # 3. Instagram'a post at
            ok = post_to_instagram(
                image_path=image_path,
                caption=deal.get("caption", deal.get("baslik", "")),
                instagram_user_id=INSTAGRAM_USER_ID,
                access_token=INSTAGRAM_TOKEN,
                imgbb_api_key=IMGBB_API_KEY,
            )

            if ok:
                success_count += 1
                print(f"  Feed yayinlandi!")

                # Story — ayrı 9:16 görsel üret ve linki ile at
                if not dry_run:
                    story_link = deal.get("kaynak_url", "https://www.instagram.com/firsatcokiyi")
                    story_path = create_story_image(deal, category, pexels_key=PEXELS_API_KEY)
                    story_url = _upload_catbox(story_path)
                    if story_url:
                        _post_story(story_url, story_link)
            else:
                print(f"  Yayinlama basarisiz.\n")

        except Exception as e:
            print(f"  HATA: {e}\n")

        if not dry_run:
            time.sleep(POST_DELAY_SECONDS)

    print(f"{'='*60}")
    print(f"  Tamamlandi: {success_count}/{len(CATEGORIES)} post basarili")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    check_env()

    # Argüman yoksa zamanla çalıştır, "--test" varsa hemen çalıştır
    if "--test" in sys.argv:
        print("TEST MODU — Görsel üretilir ama Instagram'a post atilmaz.\n")
        run_daily(dry_run=True)
    elif "--now" in sys.argv:
        print("HEMEN çalistiriliyor...\n")
        run_daily(dry_run=False)
    else:
        print(f"Bot baslatildi. Her gun 09:00'da calisacak.")
        print(f"Simdi test etmek icin: python main.py --test")
        print(f"Hemen gercek post atmak icin: python main.py --now\n")

        schedule.every().day.at("09:00").do(run_daily)

        while True:
            schedule.run_pending()
            time.sleep(30)
