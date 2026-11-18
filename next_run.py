"""GitHub'ın zamanlayıcısı bu repoda güvenilmez (saatlerce gecikip çalıştırmaları
atlıyor). Bu yüzden her çalıştırma, bir sonraki paylaşım saatine kadar bekleyip
workflow'u kendisi yeniden tetikler (zincir). Public repoda Actions dakikaları
ücretsiz olduğu için bekleme bir maliyet oluşturmaz.

Concurrency grubu aynı anda en fazla bir bekleyen çalıştırma tuttuğu için zincir
ikiye bölünmez; günlük yedek zamanlama zincir koptuysa onu yeniden başlatır.
"""
import os
import sys
import time
from datetime import datetime, timedelta

import requests

from main import TR, WINDOW

MINUTE = 23            # her saatin :23'ünde
MAX_SLEEP = 5 * 3600   # tek bir job 6 saati geçemez


def next_target(now):
    t = now.replace(minute=MINUTE, second=0, microsecond=0)
    if t <= now + timedelta(minutes=5):
        t += timedelta(hours=1)
    if not WINDOW[0] <= t.hour < WINDOW[1]:
        t = t.replace(hour=WINDOW[0])
        if t <= now:
            t += timedelta(days=1)
    return t


def main():
    now = datetime.now(TR)
    target = next_target(now)
    wait = min((target - now).total_seconds(), MAX_SLEEP)
    print(f"Sonraki çalıştırma: {target:%Y-%m-%d %H:%M} — {wait / 60:.0f} dk bekleniyor")
    sys.stdout.flush()
    time.sleep(max(0, wait))

    repo, wf = os.environ["GITHUB_REPOSITORY"], os.environ.get("WORKFLOW_FILE", "daily_post.yml")
    r = requests.post(f"https://api.github.com/repos/{repo}/actions/workflows/{wf}/dispatches",
                      headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                               "Accept": "application/vnd.github+json"},
                      json={"ref": os.environ.get("GITHUB_REF_NAME", "main")}, timeout=30)
    print(f"Yeniden tetiklendi: HTTP {r.status_code} {r.text[:200]}")
    r.raise_for_status()


if __name__ == "__main__":
    main()
