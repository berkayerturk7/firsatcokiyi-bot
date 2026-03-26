import time
import requests


def _upload_catbox(image_path: str) -> str | None:
    """catbox.moe — ücretsiz, API key gerektirmez, Instagram ile uyumlu"""
    with open(image_path, "rb") as f:
        resp = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": (image_path, f, "image/jpeg")},
            timeout=60,
        )
    if resp.status_code == 200 and resp.text.startswith("https://"):
        return resp.text.strip()
    print(f"  catbox yükleme hatası: {resp.text}")
    return None


def post_to_instagram(
    image_path: str,
    caption: str,
    instagram_user_id: str,
    access_token: str,
    imgbb_api_key: str = "",  # artık kullanılmıyor
) -> bool:
    # 1. Görseli barındır
    image_url = _upload_catbox(image_path)
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
