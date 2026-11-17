"""Amazon.com.tr'deki 365/90 günün en düşük fiyatlı ürünlerinden her çalıştırmada
10 tanesini Instagram'a paylaşır (günde iki kez: 10:00 ve 14:00). Daha önce
paylaşılan ürünler posted.json'da tutulur ve bir daha seçilmez.

    python main.py              # tara, görselleri üret, commit+push, Instagram'a yayınla
    python main.py --dry-run    # sadece tara ve görselleri posts/ altına üret
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

from amazon_fetcher import scan, select
from instagram_poster import check_token, publish
from categories import categorize
from post_image import caption, create_post, create_story
from bio_page import build as build_site

HERE = Path(__file__).resolve().parent
load_dotenv(HERE / ".env")

INSTAGRAM_USER_ID = os.getenv("INSTAGRAM_USER_ID", "24422570594030577")
INSTAGRAM_TOKEN = os.getenv("INSTAGRAM_TOKEN")
POSTED_PATH = HERE / "posted.json"
POSTS_DIR = HERE / "posts"
SITE_DIR = HERE / "docs"
RUNS_PATH = HERE / "runs.json"  # hangi gün hangi slotun (10/14) yapıldığı
DAILY_COUNT = 10  # her çalıştırmada (10:00 ve 14:00)
DELAY_BETWEEN_POSTS = 20  # saniye
TR = timezone(timedelta(hours=3))


def git(*args):
    return subprocess.run(["git", *args], cwd=HERE, check=True,
                          capture_output=True, text=True).stdout.strip()


def git_commit_push(paths, message):
    git("add", *[str(p) for p in paths])
    if not git("status", "--porcelain", *[str(p) for p in paths]):
        return git("rev-parse", "HEAD")
    git("commit", "-m", message)
    git("pull", "--rebase", "--quiet")
    git("push", "--quiet")
    return git("rev-parse", "HEAD")


def repo_slug():
    if os.getenv("GITHUB_REPOSITORY"):
        return os.environ["GITHUB_REPOSITORY"]
    url = git("remote", "get-url", "origin")
    return re.sub(r"(\.git)?$", "", re.sub(r"^.*github\.com[:/]", "", url))


def wait_until_public(url, timeout=120):
    end = time.time() + timeout
    while time.time() < end:
        try:
            r = requests.head(url, timeout=15)
            if r.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(5)
    return False


def load_posted():
    if POSTED_PATH.exists():
        return json.loads(POSTED_PATH.read_text(encoding="utf-8"))
    return {}


MAX_SCHEDULE_DELAY = timedelta(hours=6)


def resolve_slot(now):
    """Bu çalıştırmanın hangi günlük slot olduğunu bulur: "10", "14" ya da "manual".

    - SLOT ortam değişkeni (dış tetikleyiciden ya da elle verilen girdi) önceliklidir.
    - GitHub zamanlaması (SCHEDULE="17 7 * * *" gibi) için slot cron saatinden çıkarılır;
      tetikleme 6 saatten fazla gecikmişse (None, gecikme) döner ve çalıştırma atlanır.
    - Hiçbiri yoksa saate göre: 12:00'den önce "10", sonra "14".
    """
    slot = os.getenv("SLOT", "").strip().lower()
    if slot in ("10", "14", "manual"):
        return slot, None
    sched = os.getenv("SCHEDULE", "").strip()
    if sched:
        minute, hour_utc = (int(x) for x in sched.split()[:2])
        local_hour = (hour_utc + 3) % 24
        intended = now.replace(hour=local_hour, minute=minute, second=0, microsecond=0)
        late = now - intended
        if late < timedelta(0):  # gece yarısını geçmiş bir dünkü tetikleme
            late += timedelta(days=1)
        if late > MAX_SCHEDULE_DELAY:
            return None, late
        return str(local_hour), late
    return ("10" if now.hour < 12 else "14"), None


def load_runs():
    if RUNS_PATH.exists():
        return json.loads(RUNS_PATH.read_text(encoding="utf-8"))
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Post atmadan sadece görsel üret")
    ap.add_argument("--count", type=int, default=DAILY_COUNT)
    ap.add_argument("--site", action="store_true", help="Sadece docs/ sayfasını üret")
    args = ap.parse_args()

    if args.site:
        print(build_site(load_posted(), repo_slug()))
        return

    now = datetime.now(TR)
    today = now.strftime("%Y-%m-%d")
    slot, late = resolve_slot(now)
    print(f"=== Amazon günlük paylaşım — {today}, slot: {slot or '-'} ===\n")

    # Aynı slot iki kez çalışmasın (dış tetikleyici + GitHub yedek zamanlaması)
    runs = load_runs()
    if not args.dry_run:
        if slot is None:
            print(f"GitHub zamanlaması {late} gecikmiş; slot kaçırıldı, çalıştırma atlanıyor.")
            return
        if slot != "manual" and slot in runs.get(today, []):
            print(f"Bugünün {slot}:00 paylaşımları zaten yapılmış; atlanıyor.")
            return

    if not args.dry_run:
        if not INSTAGRAM_TOKEN:
            sys.exit("HATA: INSTAGRAM_TOKEN tanımlı değil.")
        err = check_token(INSTAGRAM_USER_ID, INSTAGRAM_TOKEN)
        if err:
            sys.exit(f"HATA: Instagram token geçersiz: {err}\n"
                     "Meta panelinden yeni token alıp INSTAGRAM_TOKEN secret'ını güncelleyin.")

    posted = load_posted()
    print(f"Amazon taranıyor... (daha önce paylaşılan: {len(posted)} ürün)")
    found = scan()
    print(f"\n{len(found)} rozetli ürün bulundu "
          f"(365g: {sum(1 for i in found.values() if i['days'] == 365)}, "
          f"90g: {sum(1 for i in found.values() if i['days'] == 90)})")
    if not found:
        sys.exit("HATA: Amazon'dan hiç ürün alınamadı — istekler engellenmiş olabilir.")

    # Görsel üretimi başarısız olursa yedek adaylara geçebilmek için fazladan seç
    candidates = select(found, posted, count=args.count + 5)
    picks = []
    for it in candidates:
        if len(picks) == args.count:
            break
        it["cat"] = categorize(it)
        it["path"] = POSTS_DIR / today / f"{it['asin']}.jpg"
        it["story_path"] = POSTS_DIR / today / f"{it['asin']}_story.jpg"
        try:
            create_post(it, it["path"])
            create_story(it, it["cat"], it["story_path"])
        except Exception as e:
            print(f"  Görsel üretilemedi ({it['asin']}): {e}")
            continue
        picks.append(it)
        print(f"  [{it['days']}g] -%{it['discount']}  {it['cat']:<15} {it['title'][:60]}")

    if not picks:
        sys.exit("HATA: Paylaşılacak uygun ürün bulunamadı.")

    if args.dry_run:
        print(f"\n[DRY RUN] {len(picks)} post + story görseli üretildi: {POSTS_DIR / today}")
        for it in picks:
            print("\n" + "─" * 60 + "\n" + caption(it))
        return

    # Görselleri repoya commit'le; Instagram onları raw.githubusercontent.com'dan çeker
    files = [f for it in picks for f in (it["path"], it["story_path"])]
    sha = git_commit_push(files, f"Günün Amazon görselleri: {today}")
    slug = repo_slug()

    def raw(path):
        return f"https://raw.githubusercontent.com/{slug}/{sha}/{path.relative_to(HERE).as_posix()}"

    ok = stories = 0
    try:
        for n, it in enumerate(picks, 1):
            print(f"\n[{n}/{len(picks)}] {it['title'][:70]}")
            url = raw(it["path"])
            if not wait_until_public(url):
                print(f"  Görsel herkese açık adreste görünmüyor (repo public mi?): {url}")
                continue
            try:
                media_id = publish(url, caption(it), INSTAGRAM_USER_ID, INSTAGRAM_TOKEN)
            except requests.RequestException as e:
                print(f"  Ağ hatası: {e}")
                media_id = None
            if not media_id:
                continue
            ok += 1
            print(f"  ✅ Post yayınlandı ({media_id})")
            posted[it["asin"]] = {
                "date": today, "posted_at": datetime.now(TR).isoformat(timespec="seconds"),
                "days": it["days"], "price": it["price"], "old_price": it["old_price"],
                "discount": it["discount"], "title": it["title"], "category": it["cat"],
                "url": it["url"], "thumb": it["image"].replace("_AC_SL1200_", "_AC_SL400_"),
                "post_image": it["path"].relative_to(HERE).as_posix(), "media_id": media_id,
            }
            POSTED_PATH.write_text(json.dumps(posted, ensure_ascii=False, indent=1) + "\n",
                                   encoding="utf-8")

            # Story — başarısız olsa da feed postu sayılır
            try:
                story_id = publish(raw(it["story_path"]), "", INSTAGRAM_USER_ID, INSTAGRAM_TOKEN,
                                   story=True)
            except requests.RequestException as e:
                print(f"  Story ağ hatası: {e}")
                story_id = None
            if story_id:
                stories += 1
                posted[it["asin"]]["story_id"] = story_id
                POSTED_PATH.write_text(json.dumps(posted, ensure_ascii=False, indent=1) + "\n",
                                       encoding="utf-8")
                print(f"  ✅ Story yayınlandı [{it['cat']}]")

            if n < len(picks):
                time.sleep(DELAY_BETWEEN_POSTS)
    finally:
        # Ne olursa olsun paylaşılanları kaydet; sonraki çalıştırma bunları tekrar seçmesin
        if ok:
            build_site(posted, slug)
            if slot != "manual":
                runs.setdefault(today, [])
                if slot not in runs[today]:
                    runs[today].append(slot)
                # Sadece son 14 günü tut
                runs = dict(sorted(runs.items())[-14:])
                RUNS_PATH.write_text(json.dumps(runs, indent=1) + "\n", encoding="utf-8")
            git_commit_push([POSTED_PATH, SITE_DIR, RUNS_PATH],
                            f"Paylaşılanlar güncellendi: {today} {slot} (+{ok})")

    print(f"\n=== Tamamlandı: {ok}/{len(picks)} post, {stories} story yayınlandı ===")
    if ok == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
