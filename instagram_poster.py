"""Herkese açık bir görsel URL'sinden Instagram feed postu yayınlar."""
import time

import requests

API = "https://graph.instagram.com/v21.0"


def check_token(user_id, token):
    """Token geçerliyse None, değilse hata mesajı döndürür."""
    try:
        r = requests.get(f"{API}/me", params={"fields": "user_id", "access_token": token}, timeout=20)
    except requests.RequestException as e:
        print(f"UYARI: Token kontrolü yapılamadı ({e}), devam ediliyor.")
        return None
    if r.status_code == 200:
        return None
    try:
        return r.json()["error"]["message"]
    except (ValueError, KeyError, TypeError):
        return f"{r.status_code} {r.text[:200]}"


def publish(image_url, caption, user_id, token, story=False):
    """Feed postu (veya story=True ise story) yayınlar; başarılıysa media id, değilse None.
    Not: API story'ye link sticker eklemeyi desteklemiyor."""
    data = {"image_url": image_url, "access_token": token}
    if story:
        data["media_type"] = "STORIES"
    else:
        data["caption"] = caption
    c = requests.post(f"{API}/{user_id}/media", data=data, timeout=60)
    if c.status_code != 200:
        print(f"  Container hatası: {c.text[:300]}")
        return None
    cid = c.json()["id"]

    # Instagram görseli indirip işleyene kadar bekle
    for _ in range(20):
        s = requests.get(f"{API}/{cid}", params={"fields": "status_code", "access_token": token},
                         timeout=20).json()
        status = s.get("status_code")
        if status == "FINISHED":
            break
        if status == "ERROR":
            print(f"  Instagram görseli işleyemedi: {s}")
            return None
        time.sleep(3)

    p = requests.post(f"{API}/{user_id}/media_publish",
                      data={"creation_id": cid, "access_token": token}, timeout=60)
    if p.status_code != 200:
        print(f"  Yayınlama hatası: {p.text[:300]}")
        return None
    return p.json().get("id")
