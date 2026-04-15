import time
import requests


def _upload_litterbox(image_path: str) -> str | None:
    """litterbox.catbox.moe — geçici (72 saat), catbox ile aynı CDN, Instagram uyumlu"""
    try:
        with open(image_path, "rb") as f:
            resp = requests.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                data={"reqtype": "fileupload", "time": "72h"},
                files={"fileToUpload": (image_path, f, "image/jpeg")},
                timeout=60,
            )
        if resp.status_code == 200 and resp.text.startswith("https://"):
            return resp.text.strip()
        print(f"  litterbox yükleme hatası: {resp.text[:200]}")
    except Exception as e:
        print(f"  litterbox hata: {e}")
    return None


def _upload_0x0(image_path: str) -> str | None:
    """0x0.st — anonim dosya barındırma, doğrudan URL, Instagram uyumlu"""
    try:
        with open(image_path, "rb") as f:
            resp = requests.post(
                "https://0x0.st",
                files={"file": (image_path, f, "image/jpeg")},
                timeout=60,
            )
        if resp.status_code == 200 and resp.text.strip().startswith("https://"):
            return resp.text.strip()
        print(f"  0x0.st yükleme hatası: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        print(f"  0x0.st hata: {e}")
    return None


def _upload_catbox(image_path: str) -> str | None:
    """catbox.moe — bazen kapalı olabiliyor, son yedek"""
    try:
        with open(image_path, "rb") as f:
            resp = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": (image_path, f, "image/jpeg")},
                timeout=60,
            )
        if resp.status_code == 200 and resp.text.startswith("https://"):
            return resp.text.strip()
        print(f"  catbox yükleme hatası: {resp.text[:200]}")
    except Exception as e:
        print(f"  catbox hata: {e}")
    return None


def _upload_image(image_path: str, imgbb_api_key: str = "") -> str | None:
    """
    Öncelik sırası: litterbox → 0x0.st → catbox
    (imgbb Instagram tarafından kabul edilmiyor — bloke)
    """
    print("  litterbox deneniyor...")
    url = _upload_litterbox(image_path)
    if url:
        print(f"  litterbox'a yüklendi ✓")
        return url

    print("  0x0.st deneniyor...")
    url = _upload_0x0(image_path)
    if url:
        print(f"  0x0.st'ye yüklendi ✓")
        return url

    print("  catbox deneniyor...")
    url = _upload_catbox(image_path)
    if url:
        print(f"  catbox'a yüklendi ✓")
        return url

    print("  Tüm görsel barındırma servisleri başarısız!")
    return None


def post_to_instagram(
    image_path: str,
    caption: str,
    instagram_user_id: str,
    access_token: str,
    imgbb_api_key: str = "",
) -> bool:
    # 1. Görseli barındır
    image_url = _upload_image(image_path, imgbb_api_key)
    if not image_url:
        return False
    print(f"  Görsel URL: {image_url}")

    # 2. Media container oluştur
    container_resp = requests.post(
        f"https://graph.instagram.com/v21.0/{instagram_user_id}/media",
        data={
            "image_url":    image_url,
            "caption":      caption,
            "access_token": access_token,
        },
        timeout=30,
    )
    if container_resp.status_code != 200:
        print(f"  Container hatası: {container_resp.text}")
        return False

    container_id = container_resp.json().get("id")
    print(f"  Container ID: {container_id}")

    # 3. Container hazır olana kadar bekle
    time.sleep(8)

    # 4. Yayınla
    publish_resp = requests.post(
        f"https://graph.instagram.com/v21.0/{instagram_user_id}/media_publish",
        data={
            "creation_id":  container_id,
            "access_token": access_token,
        },
        timeout=30,
    )
    if publish_resp.status_code == 200:
        print(f"  ✅ Yayınlandı! Post ID: {publish_resp.json().get('id')}")
        return True

    print(f"  Yayınlama hatası: {publish_resp.text}")
    return False
