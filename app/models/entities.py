"""Definisi skema database SQLAlchemy untuk SUKU-Monitor.

Mencakup:
- Article: berita dari media online, Google News, dan website kampus
- IgMedia: postingan Instagram resmi kampus
- IgComment: komentar di postingan Instagram
- Keyword: daftar kata kunci pencarian
- Campus: daftar kampus pembanding & PTKIN
- PmbData: data pendaftaran PMB untuk korelasi
- AuditLog: catatan koreksi label manusia
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Index
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Article(Base):
    """Tabel artikel berita."""
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(1000), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    source_name = Column(String(150), nullable=False, index=True)  # contoh: Detik, Suara Merdeka, UIN Walisongo
    source_type = Column(String(50), default="media_online", index=True)  # media_online / ptkin_web / kemenag_web
    author = Column(String(200), nullable=True)
    published_at = Column(DateTime, nullable=True, index=True)
    crawled_at = Column(DateTime, default=datetime.utcnow, index=True)

    content = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=True, index=True)  # SHA256 untuk deduplikasi

    # Klasifikasi
    sentiment = Column(String(20), default="belum_dinilai", index=True)  # positif / netral / negatif
    sentiment_score = Column(Float, nullable=True)  # -1.0 s.d. +1.0
    sentiment_reason = Column(Text, nullable=True)

    is_sensitive = Column(Boolean, default=False, index=True)
    sensitive_category = Column(String(50), nullable=True, index=True)  # sara / kekerasan_seksual / demo / lainnya
    sensitive_reason = Column(Text, nullable=True)

    topic = Column(String(100), nullable=True, index=True)  # pmb / akademik / prestasi / tata_kelola / dll.
    matched_keyword = Column(String(100), nullable=True)

    # Status verifikasi manusia
    is_verified = Column(Boolean, default=False)
    verified_by = Column(String(100), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    # Entitas yang terdeteksi
    detected_entities = Column(Text, nullable=True)  # JSON-string daftar nama dosen/pejabat
    lecturer_name = Column(String(200), nullable=True, index=True)  # Nama dosen terkait jika ada


class Lecturer(Base):
    """Tabel database profil dosen & pimpinan UIN Sunan Kudus."""
    __tablename__ = "lecturers"

    id = Column(Integer, primary_key=True)
    full_name = Column(String(250), unique=True, nullable=False)
    clean_name = Column(String(200), nullable=False, index=True)
    alias = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class IgMedia(Base):
    """Tabel media postingan Instagram kampus."""
    __tablename__ = "ig_media"

    id = Column(String(100), primary_key=True)  # ID dari Instagram
    caption = Column(Text, nullable=True)
    media_type = Column(String(50), nullable=True)  # IMAGE, VIDEO, CAROUSEL_ALBUM
    media_url = Column(String(1000), nullable=True)
    permalink = Column(String(500), nullable=True)
    timestamp = Column(DateTime, nullable=True, index=True)
    crawled_at = Column(DateTime, default=datetime.utcnow)

    like_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)

    # Analisis isi caption
    topic = Column(String(100), nullable=True)
    is_pmb_related = Column(Boolean, default=False, index=True)

    comments = relationship("IgComment", back_populates="media", cascade="all, delete-orphan")


class IgComment(Base):
    """Tabel komentar di postingan Instagram."""
    __tablename__ = "ig_comments"

    id = Column(String(100), primary_key=True)  # ID komentar IG
    media_id = Column(String(100), ForeignKey("ig_media.id"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=True)
    username = Column(String(100), nullable=True)

    sentiment = Column(String(20), default="belum_dinilai", index=True)  # positif / netral / negatif
    emotion = Column(String(50), nullable=True)  # trust, joy, surprise, anger, sadness, fear
    is_sensitive = Column(Boolean, default=False)

    media = relationship("IgMedia", back_populates="comments")


class Keyword(Base):
    """Daftar kata kunci pencarian."""
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True)
    keyword = Column(String(200), unique=True, nullable=False)
    category = Column(String(50), default="kampus")  # kampus / pimpinan / dosen / pmb
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Campus(Base):
    """Daftar kampus pembanding & PTKIN."""
    __tablename__ = "campuses"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    short_name = Column(String(50), nullable=True)
    category = Column(String(50), default="ptkin")  # ptkin / pembanding / kemenag
    website_url = Column(String(300), nullable=True)
    is_benchmark = Column(Boolean, default=False)  # Apakah jadi pembanding share of voice


class PmbData(Base):
    """Data pendaftar PMB untuk korelasi dengan publikasi."""
    __tablename__ = "pmb_data"

    id = Column(Integer, primary_key=True)
    year = Column(Integer, nullable=False, index=True)
    track_name = Column(String(100), nullable=False)  # SPAN-PTKIN, UM-PTKIN, Mandiri, dll.
    batch = Column(String(50), nullable=True)  # Gelombang 1, Gelombang 2
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    total_applicants = Column(Integer, default=0)
    total_accepted = Column(Integer, default=0)
    total_enrolled = Column(Integer, default=0)


class AuditLog(Base):
    """Log perubahan label oleh manusia (menjaga prinsip netral & dapat diaudit)."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    action = Column(String(100), nullable=False)  # koreksi_sentimen / koreksi_sensitif
    old_value = Column(String(200), nullable=True)
    new_value = Column(String(200), nullable=True)
    user_identifier = Column(String(100), default="admin")
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
