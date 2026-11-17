"""Orkestrator pipeline pengumpulan data & klasifikasi berita."""

from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.entities import Article, Keyword
from app.models.database import SessionLocal
from app.crawlers.google_news import search_google_news_rss
from app.crawlers.article_extractor import extract_article_content
from app.classifiers.gemini_classifier import classify_article


DEFAULT_KEYWORDS = [
    ("UIN Sunan Kudus", "kampus"),
    ("UIN Kudus", "kampus"),
    ("IAIN Kudus", "kampus"),
    ("STAIN Kudus", "kampus"),
    ("PMB UIN Kudus", "pmb"),
    ("Rektor UIN Sunan Kudus", "pimpinan"),
    ("Mahasiswa UIN Kudus", "kampus"),
]


def init_default_keywords(db: Session):
    """Menambahkan kata kunci awal jika tabel masih kosong."""
    if db.query(Keyword).count() == 0:
        for kw, cat in DEFAULT_KEYWORDS:
            db.add(Keyword(keyword=kw, category=cat, is_active=True))
        db.commit()


def run_pipeline_for_keyword(db: Session, keyword: str, max_articles: int = 15) -> int:
    """Menjalankan pipeline pengumpulan & klasifikasi untuk satu kata kunci.
    
    Langkah:
    1. Search Google News RSS
    2. Cek apakah URL sudah pernah disimpan (deduplikasi)
    3. Jika baru: ekstrak isi artikel via trafilatura
    4. Klasifikasi sentimen & sensitif via Gemini / rule-based
    5. Simpan ke database
    """
    items = search_google_news_rss(keyword)
    saved_count = 0

    for item in items[:max_articles]:
        raw_url = item["url"]

        # Cek duplikat awal berdasarkan URL
        existing = db.query(Article).filter(Article.url == raw_url).first()
        if existing:
            continue

        # Ekstraksi konten artikel
        extracted = extract_article_content(raw_url)
        content = extracted.get("content", "")
        final_url = extracted.get("final_url", raw_url)
        content_hash = extracted.get("content_hash", "")

        # Cek duplikat konten (rilis yang sama di media berbeda)
        # Jika rilis sama sudah ada, kita tetap simpan agar tercatat di 'Top Media'
        # tetapi klasifikasi bisa kita hemat.

        # Klasifikasi menggunakan Gemini
        title = item["title"]
        classification = classify_article(title=title, content=content)

        # Buat objek artikel
        article = Article(
            url=raw_url,
            title=title,
            source_name=item["source_name"],
            source_type=item.get("source_type", "media_online"),
            author=extracted.get("author"),
            published_at=item["published_at"],
            crawled_at=datetime.utcnow(),
            content=content,
            content_hash=content_hash,
            summary=classification.get("summary"),
            sentiment=classification.get("sentiment", "netral"),
            sentiment_score=classification.get("sentiment_score", 0.0),
            sentiment_reason=classification.get("sentiment_reason"),
            is_sensitive=classification.get("is_sensitive", False),
            sensitive_category=classification.get("sensitive_category"),
            sensitive_reason=classification.get("sensitive_reason"),
            topic=classification.get("topic", "lainnya"),
            matched_keyword=keyword,
        )

        db.add(article)
        db.commit()
        saved_count += 1

    return saved_count


def run_full_crawler_cycle(max_per_keyword: int = 10) -> Dict[str, Any]:
    """Menjalankan crawling lengkap untuk semua kata kunci yang aktif."""
    db = SessionLocal()
    try:
        init_default_keywords(db)
        keywords = db.query(Keyword).filter(Keyword.is_active == True).all()

        total_saved = 0
        details = {}

        for kw in keywords:
            count = run_pipeline_for_keyword(db, kw.keyword, max_articles=max_per_keyword)
            details[kw.keyword] = count
            total_saved += count

        return {
            "status": "success",
            "total_saved": total_saved,
            "details": details,
            "timestamp": datetime.utcnow().isoformat(),
        }
    finally:
        db.close()
