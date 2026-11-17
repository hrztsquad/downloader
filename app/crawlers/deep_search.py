"""Modul Deep Search multi-sudut dan multi-mesin untuk SUKU-Monitor.

Mencakup:
1. Windowed Time Crawl: Memecah rentang waktu 2 tahun terakhir (2024 - 2026) per kuartal/semester
   agar Google News tidak membatasi output hanya 10-60 berita terbaru.
2. Multi-Entity Keywords: Mencari variasi 'UIN Sunan Kudus', 'UIN Kudus', 'IAIN Kudus',
   'STAIN Kudus', nama Rektor, PMB, serta dosen/tendik.
3. Portal-Targeted Search: Pencarian langsung ke portal lokal Muria (Murianews, Suara Merdeka,
   Radar Kudus, Kemenag RI, dan jaringan PTKIN).
"""

import os
import urllib.parse
from datetime import datetime, timedelta
from typing import List, Dict, Any, Set
import feedparser
import httpx

for env_key in ("NO_PROXY", "no_proxy"):
    if env_key in os.environ and "[::1]" in os.environ[env_key]:
        os.environ[env_key] = os.environ[env_key].replace("[::1]", "").strip(",")


def generate_time_windows(years: int = 2, step_months: int = 6) -> List[tuple]:
    """Menghasilkan pasangan (start_date, end_date) dalam format YYYY-MM-DD
    selama N tahun terakhir untuk memecah query.
    """
    windows = []
    now = datetime.utcnow()
    total_steps = (years * 12) // step_months

    current_end = now
    for _ in range(total_steps):
        current_start = current_end - timedelta(days=step_months * 30)
        start_str = current_start.strftime("%Y-%m-%d")
        end_str = current_end.strftime("%Y-%m-%d")
        windows.append((start_str, end_str))
        current_end = current_start

    return windows


def deep_search_google_news(
    base_keywords: List[str] = None,
    include_history_2years: bool = True,
    target_domains: List[str] = None,
) -> List[Dict[str, Any]]:
    """Menjalankan Deep Search Google News dengan pemecahan jendela waktu 2 tahun
    dan pencarian terarah ke domain-domain penting.
    """
    if base_keywords is None:
        base_keywords = [
            '"UIN Sunan Kudus"',
            '"UIN Kudus"',
            '"IAIN Kudus"',
            '"STAIN Kudus"',
            '"Rektor UIN Sunan Kudus"',
            '"Rektor IAIN Kudus"',
            '"PMB UIN Kudus"',
            '"PMB IAIN Kudus"',
        ]

    queries = []

    # 1. Query dasar
    for kw in base_keywords:
        queries.append(kw)

    # 2. Query jendela waktu (2 tahun ke belakang per 6 bulan)
    if include_history_2years:
        windows = generate_time_windows(years=2, step_months=6)
        core_entities = ['"UIN Sunan Kudus"', '"IAIN Kudus"']
        for ent in core_entities:
            for start, end in windows:
                queries.append(f"{ent} after:{start} before:{end}")

    # 3. Query terarah ke domain lokal & Kemenag
    domains = target_domains or [
        "murianews.com",
        "suaramerdeka.com",
        "kemenag.go.id",
        "pendis.kemenag.go.id",
        "radarkudus.jawapos.com",
    ]
    for d in domains:
        queries.append(f'("UIN Kudus" OR "IAIN Kudus" OR "UIN Sunan Kudus") site:{d}')

    # Eksekusi pencarian
    results = []
    seen_urls: Set[str] = set()

    with httpx.Client(timeout=15, follow_redirects=True) as client:
        for q in queries:
            encoded_query = urllib.parse.quote(q)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=id&gl=ID&ceid=ID:id"

            try:
                resp = client.get(rss_url)
                feed = feedparser.parse(resp.text)
            except Exception as e:
                print(f"[WARN] Deep search feed gagal untuk '{q[:40]}': {e}")
                continue

            for entry in feed.entries:
                link = entry.get("link", "")
                if not link or link in seen_urls:
                    continue
                seen_urls.add(link)

                title = entry.get("title", "")
                source_name = "Media Online"
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title = parts[0].strip()
                    source_name = parts[1].strip()
                elif hasattr(entry, "source") and hasattr(entry.source, "title"):
                    source_name = entry.source.title

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
                    "matched_keyword": q,
                })

    return results
