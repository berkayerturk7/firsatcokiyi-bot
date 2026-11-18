"""Her çalıştırmanın özetini GitHub'da günlük bir issue'ya yorum olarak yazar.
Repoyu "Watch → All activity" ile izleyen hesaba GitHub her yorum için e-posta gönderir
(kullanıcı adı herkese açık issue'da görünmesin diye mention kullanılmıyor)."""
import os

import requests

GH = "https://api.github.com"
PREFIX = "📬 Paylaşım raporu — "


def _headers():
    return {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "Accept": "application/vnd.github+json"}


def notify(slug, day, body):
    """GITHUB_TOKEN yoksa (yerel çalıştırma) sadece ekrana yazar."""
    if not os.getenv("GITHUB_TOKEN"):
        print("\n[bildirim — yerel, gönderilmedi]\n" + body)
        return
    try:
        title = PREFIX + day
        r = requests.get(f"{GH}/repos/{slug}/issues", headers=_headers(), timeout=20,
                         params={"state": "open", "per_page": 50})
        r.raise_for_status()
        issues = [i for i in r.json() if i["title"].startswith(PREFIX) and "pull_request" not in i]
        issue = next((i for i in issues if i["title"] == title), None)
        if issue is None:
            r = requests.post(f"{GH}/repos/{slug}/issues", headers=_headers(), timeout=20, json={
                "title": title,
                "body": f"{day} tarihli Instagram paylaşımları. Botun her çalıştırması bu "
                        "konuya yorum olarak eklenir.",
            })
            r.raise_for_status()
            issue = r.json()
            for old in issues:  # önceki günlerin raporlarını kapat
                requests.patch(f"{GH}/repos/{slug}/issues/{old['number']}", headers=_headers(),
                               timeout=20, json={"state": "closed"})
        r = requests.post(f"{GH}/repos/{slug}/issues/{issue['number']}/comments",
                          headers=_headers(), timeout=20, json={"body": body})
        r.raise_for_status()
        print(f"Bildirim gönderildi: {issue['html_url']}")
    except Exception as e:
        print(f"UYARI: Bildirim gönderilemedi: {e}")
