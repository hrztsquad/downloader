"""Ekstraktor isi artikel dari URL menggunakan trafilatura & httpx."""

import os
import hashlib
from typing import Optional, Dict, Any
import httpx
import trafilatura

for env_key in ("NO_PROXY", "no_proxy"):
    if env_key in os.environ and "[::1]" in os.environ[env_key]:
        os.environ[env_key] = os.environ[env_key].replace("[::1]", "").strip(",")


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id,en-US;q=0.7,en;q=0.3",
}


def extract_article_content(url: str, timeout: int = 15) -> Dict[str, Any]:
    """Mengambil halaman web dan mengekstrak teks utama artikel, penulis, dan tanggal.
    
    Membersihkan iklan, menu navigasi, dan footer secara otomatis.
    """
    result = {
        "final_url": url,
        "content": "",
        "author": None,
        "content_hash": "",
        "status": "success",
    }

    try:
        # Ikuti redirect (penting untuk link Google News yang berbentuk wrapper)
        with httpx.Client(follow_redirects=True, timeout=timeout, headers=HEADERS) as client:
            resp = client.get(url)
            result["final_url"] = str(resp.url)
            html = resp.text

        # Ekstraksi menggunakan trafilatura
        extracted = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
            output_format="txt",
        )

        metadata = trafilatura.extract_metadata(html)

        if extracted:
            result["content"] = extracted.strip()
            # Hitung SHA256 dari konten untuk deduplikasi
            clean_sample = "".join(extracted.split())[:1000].lower()
            result["content_hash"] = hashlib.sha256(clean_sample.encode("utf-8")).hexdigest()
        else:
            result["status"] = "no_content_extracted"

        if metadata:
            if metadata.author:
                result["author"] = metadata.author
            if metadata.title and not result.get("title"):
                result["title"] = metadata.title

    except Exception as e:
        result["status"] = f"error: {str(e)[:150]}"

    return result
