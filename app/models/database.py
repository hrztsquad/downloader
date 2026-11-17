"""Inisialisasi koneksi database dan session SQLAlchemy."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models.entities import Base

# Buat engine (support SQLite & PostgreSQL)
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Membuat semua tabel jika belum ada."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency FastAPI untuk session database per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
