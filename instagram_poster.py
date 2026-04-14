import base64
import time
import requests


def _upload_imgbb(image_path: str, api_key: str) -> str | None:
    """imgbb.com — API key ile yükle, Instagram ile uyumlu"""
    if not api_key:
        return None
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    resp = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": api_key, "image": b64},
        timeout=60,
    )
    if resp.status_code == 200:
        url = resp.json().get("data", {}).get("url")
        if url:
            return url
    print(f"  imgbb yükleme hatası: {resp.text[:200]}")
    return None


def _upload_catbox(image_path: str) -> str | None:
    """catbox.moe — ücretsiz yedek, API key gerektirmez"""
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
    return None


def _upload_image(image_path: str, imgbb_api_key: str = "") -> str | None:
    """imgbb birincil, catbox yedek"""
    url = _upload_imgbb(image_path, imgbb_api_key)
    if url:
        print(f"  imgbb'ye yüklendi ✓")
        return url
    print("  imgbb başarısız, catbox deneniyor...")
    return _upload_catbox(image_path)


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
