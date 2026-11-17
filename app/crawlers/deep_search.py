"""Modul Deep Search multi-sudut dan multi-mesin untuk SUKU-Monitor.

Mencakup:
1. Windowed Time Crawl: Memecah rentang waktu 2 tahun terakhir (2024 - 2026) per semester.
2. Multi-Entity Keywords: Mencari variasi 'UIN Sunan Kudus', 'UIN Kudus', 'IAIN Kudus', 'STAIN Kudus'.
3. 18 Target Media Lokal & Nasional: Murianews, Radar Kudus, Beta News, Jurnal Pantura,
   ISK News, Klikfakta, Suara Merdeka, Tribun Jateng, Lingkar Jateng, Zonanews, Lintas Kudus, dll.
4. 250+ Dosen & Pimpinan: Pencarian nama dosen + konteks Kudus/UIN/IAIN di media massa dan PTKIN.
"""

import os
import urllib.parse
from datetime import datetime, timedelta
from typing import List, Dict, Any, Set
import feedparser
import httpx
from app.data.sources import TARGET_MEDIA, PTKIN_DOMAINS, get_curated_lecturers

for env_key in ("NO_PROXY", "no_proxy"):
    if env_key in os.environ and "[::1]" in os.environ[env_key]:
        os.environ[env_key] = os.environ[env_key].replace("[::1]", "").strip(",")


def generate_time_windows(years: int = 2, step_months: int = 6) -> List[tuple]:
    """Menghasilkan pasangan (start_date, end_date) format YYYY-MM-DD."""
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


def build_deep_search_queries() -> List[Dict[str, str]]:
    """Membangun matriks query lengkap untuk 4 divisi robot."""
    queries = []

    # 1. Query Dasar & Windowing Waktu 2 Tahun
    windows = generate_time_windows(years=2, step_months=6)
    core_terms = ['"UIN Sunan Kudus"', '"UIN Kudus"', '"IAIN Kudus"', '"STAIN Kudus"']
    for term in core_terms:
        queries.append({"q": term, "category": "kampus_umum"})
        for start, end in windows:
            queries.append({
                "q": f"{term} after:{start} before:{end}",
                "category": "kampus_2tahun",
            })

    # 2. Query 18 Media Lokal & Nasional
    for m in TARGET_MEDIA:
        domain = m["domain"]
        queries.append({
            "q": f'("UIN Kudus" OR "IAIN Kudus" OR "Sunan Kudus" OR "STAIN Kudus") site:{domain}',
            "category": f"media_{m['category']}",
            "source_hint": m["name"],
        })

    # 3. Query Jaringan PTKIN Se-Indonesia
    for pt in PTKIN_DOMAINS:
        queries.append({
            "q": f'("UIN Sunan Kudus" OR "IAIN Kudus" OR "UIN Kudus") site:{pt["domain"]}',
            "category": "ptkin_network",
            "source_hint": pt["name"],
        })

    # 4. Query Nama Dosen Terpilih (Nama Inti + Konteks Kudus)
    lecturers = get_curated_lecturers()
    for lec in lecturers:
        clean = lec["clean_name"]
        alias = lec["alias"]
        if alias:
            q_lec = f'("{clean}" OR "{alias}") ("Kudus" OR "UIN" OR "IAIN")'
        else:
            q_lec = f'"{clean}" ("Kudus" OR "UIN" OR "IAIN")'

        queries.append({
            "q": q_lec,
            "category": "dosen",
            "lecturer_name": lec["full_name"],
        })

    return queries


def execute_deep_search(max_queries: int = 150) -> List[Dict[str, Any]]:
    """Mengeksekusi Deep Search dan menghasilkan daftar metadata artikel unik."""
    all_queries = build_deep_search_queries()
    results = []
    seen_urls: Set[str] = set()

    with httpx.Client(timeout=15, follow_redirects=True) as client:
        for q_obj in all_queries[:max_queries]:
            q_text = q_obj["q"]
            encoded_query = urllib.parse.quote(q_text)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=id&gl=ID&ceid=ID:id"

            try:
                resp = client.get(rss_url)
                feed = feedparser.parse(resp.text)
            except Exception as e:
                continue

            for entry in feed.entries:
                link = entry.get("link", "")
                if not link or link in seen_urls:
                    continue
                seen_urls.add(link)

                title = entry.get("title", "")
                source_name = q_obj.get("source_hint", "Media Online")
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
                    "source_type": q_obj.get("category", "media_online"),
                    "published_at": pub_date,
                    "matched_keyword": q_text,
                    "lecturer_name": q_obj.get("lecturer_name"),
                })

    return results
