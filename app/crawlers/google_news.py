"""Crawler Google News RSS untuk pencarian kata kunci bahasa Indonesia."""

import os
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any
import feedparser
import httpx

# Bersihkan IPv6 '[::1]' dari NO_PROXY yang bisa membuat httpx crash pada beberapa versi
for env_key in ("NO_PROXY", "no_proxy"):
    if env_key in os.environ and "[::1]" in os.environ[env_key]:
        os.environ[env_key] = os.environ[env_key].replace("[::1]", "").strip(",")


def search_google_news_rss(query: str, hl: str = "id", gl: str = "ID", ceid: str = "ID:id") -> List[Dict[str, Any]]:
    """Mencari artikel lewat feed Google News RSS berdasarkan kata kunci.
    
    Menghasilkan list metadata artikel: title, link, published_at, source_name.
    """
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl={hl}&gl={gl}&ceid={ceid}"

    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(rss_url)
            feed = feedparser.parse(resp.text)
    except Exception as e:
        print(f"[WARN] Gagal fetch Google News RSS untuk '{query}': {e}")
        return []

    results = []

    for entry in feed.entries:
        title = entry.get("title", "")
        link = entry.get("link", "")
        
        # Ekstrak nama media dari title (biasanya "Judul Berita - Nama Media")
        source_name = "Media Online"
        if " - " in title:
            parts = title.rsplit(" - ", 1)
            title = parts[0].strip()
            source_name = parts[1].strip()
        elif hasattr(entry, "source") and hasattr(entry.source, "title"):
            source_name = entry.source.title

        # Tanggal publikasi
        pub_date = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                pub_date = datetime(*entry.published_parsed[:6])
            except Exception:
                pub_date = datetime.utcnow()
        else:
            pub_date = datetime.utcnow()

        results.append({
            "url": link,
            "title": title,
            "source_name": source_name,
            "source_type": "media_online",
            "published_at": pub_date,
            "matched_keyword": query,
        })

    return results
