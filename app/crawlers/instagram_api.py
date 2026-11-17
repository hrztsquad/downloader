"""Integrasi Instagram Graph API untuk akun resmi @uinsunankudus_."""

import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import httpx
from app.config import settings

for env_key in ("NO_PROXY", "no_proxy"):
    if env_key in os.environ and "[::1]" in os.environ[env_key]:
        os.environ[env_key] = os.environ[env_key].replace("[::1]", "").strip(",")

GRAPH_BASE = "https://graph.facebook.com/v21.0"


def fetch_account_profile() -> Dict[str, Any]:
    """Mengambil informasi profil akun Instagram kampus."""
    if not settings.ig_access_token or not settings.ig_account_id:
        return {"error": "Kredensial Instagram belum lengkap"}

    url = f"{GRAPH_BASE}/{settings.ig_account_id}"
    params = {
        "fields": "id,username,name,followers_count,media_count,profile_picture_url",
        "access_token": settings.ig_access_token,
    }

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, params=params)
            return resp.json()
    except Exception as e:
        return {"error": str(e)}


def fetch_recent_posts(limit: int = 25) -> List[Dict[str, Any]]:
    """Mengambil daftar postingan terbaru (caption, like, comments_count, permalink, timestamp)."""
    if not settings.ig_access_token or not settings.ig_account_id:
        return []

    url = f"{GRAPH_BASE}/{settings.ig_account_id}/media"
    params = {
        "fields": "id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count",
        "limit": limit,
        "access_token": settings.ig_access_token,
    }

    try:
        with httpx.Client(timeout=20) as client:
            resp = client.get(url, params=params)
            data = resp.json()
            return data.get("data", [])
    except Exception as e:
        print(f"[ERROR] Gagal fetch IG posts: {e}")
        return []


def fetch_post_comments(media_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Mengambil komentar pada suatu postingan untuk analisis sentimen & emosi audiens."""
    if not settings.ig_access_token:
        return []

    url = f"{GRAPH_BASE}/{media_id}/comments"
    params = {
        "fields": "id,text,timestamp,username,like_count",
        "limit": limit,
        "access_token": settings.ig_access_token,
    }

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, params=params)
            data = resp.json()
            return data.get("data", [])
    except Exception as e:
        print(f"[ERROR] Gagal fetch komentar untuk media {media_id}: {e}")
        return []


def fetch_tagged_posts(limit: int = 15) -> List[Dict[str, Any]]:
    """Mengambil postingan dari pihak luar yang menandai (@tag) akun kampus."""
    if not settings.ig_access_token or not settings.ig_account_id:
        return []

    url = f"{GRAPH_BASE}/{settings.ig_account_id}/tags"
    params = {
        "fields": "id,caption,media_type,permalink,timestamp,username",
        "limit": limit,
        "access_token": settings.ig_access_token,
    }

    try:
        with httpx.Client(timeout=20) as client:
            resp = client.get(url, params=params)
            data = resp.json()
            return data.get("data", [])
    except Exception as e:
        print(f"[ERROR] Gagal fetch tagged posts: {e}")
        return []
