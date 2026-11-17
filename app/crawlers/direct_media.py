"""Modul Direct Media Search (Membuka Landing Page Asli Media Tanpa Lewat Google).

Solusi mengatasi bot challenge / automated query blocking Google News:
Langsung mengambil feed pencarian asli dari media yang bersangkutan:
- Klikfakta: https://klikfakta.com/?s={query}&feed=rss2
- Beta News: https://betanews.id/?s={query}&feed=rss2
- Jurnal Pantura: https://jurnalpantura.id/?s={query}&feed=rss2
- Kaifa News: https://kaifanews.com/?s={query}&feed=rss2
- Zonasi ID: https://zonasi.id/?s={query}&feed=rss2
- Antaranews Jateng, dll.

Hasil URL yang tersimpan adalah 100% URL landing page asli media (bukan wrapper Google).
"""

import os
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any, Set
import feedparser
import httpx

for env_key in ("NO_PROXY", "no_proxy"):
    if env_key in os.environ and "[::1]" in os.environ[env_key]:
        os.environ[env_key] = os.environ[env_key].replace("[::1]", "").strip(",")

DIRECT_SEARCH_ENDPOINTS = [
    {"name": "Klikfakta", "base": "https://klikfakta.com/?s={query}&feed=rss2"},
    {"name": "Beta News", "base": "https://betanews.id/?s={query}&feed=rss2"},
    {"name": "Jurnal Pantura", "base": "https://jurnalpantura.id/?s={query}&feed=rss2"},
    {"name": "Kaifa News", "base": "https://kaifanews.com/?s={query}&feed=rss2"},
    {"name": "Zonasi ID", "base": "https://www.zonasi.id/?s={query}&feed=rss2"},
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


def search_direct_media(query: str = "UIN Sunan Kudus") -> List[Dict[str, Any]]:
    """Mencari langsung ke mesin pencari internal media lokal dan menghasilkan link landing page asli murni."""
    results = []
    seen_urls: Set[str] = set()

    with httpx.Client(timeout=12, follow_redirects=True, headers=HEADERS) as client:
        for ep in DIRECT_SEARCH_ENDPOINTS:
            name = ep["name"]
            url = ep["base"].format(query=urllib.parse.quote(query))

            try:
                resp = client.get(url)
                feed = feedparser.parse(resp.text)
            except Exception:
                continue

            for entry in feed.entries:
                direct_link = entry.get("link", "")
                if not direct_link or direct_link in seen_urls:
                    continue
                seen_urls.add(direct_link)

                title = entry.get("title", "")
                pub_date = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        pub_date = datetime(*entry.published_parsed[:6])
                    except Exception:
                        pub_date = datetime.utcnow()
                else:
                    pub_date = datetime.utcnow()

                results.append({
                    "url": direct_link,  # 100% Link Asli Landing Page!
                    "title": title,
                    "source_name": name,
                    "source_type": "media_lokal_direct",
                    "published_at": pub_date,
                    "matched_keyword": query,
                })

    return results
