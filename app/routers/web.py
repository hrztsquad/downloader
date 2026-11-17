"""Router antarmuka Web Dashboard SUKU-Monitor."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Request, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.models.database import get_db
from app.models.entities import Article, IgMedia, IgComment, Keyword, AuditLog
from app.pipeline import run_pipeline_for_keyword
from app.crawlers.instagram_api import fetch_recent_posts, fetch_post_comments
import io
import openpyxl

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def dashboard_overview(request: Request, db: Session = Depends(get_db)):
    """Halaman utama ringkasan monitoring (Modul 1-5 & 11)."""
    # Total artikel
    total_articles = db.query(Article).count()
    total_positive = db.query(Article).filter(Article.sentiment == "positif").count()
    total_neutral = db.query(Article).filter(Article.sentiment == "netral").count()
    total_negative = db.query(Article).filter(Article.sentiment == "negatif").count()
    total_sensitive = db.query(Article).filter(Article.is_sensitive == True).count()

    # Berita sensitif terbaru (alert)
    sensitive_articles = (
        db.query(Article)
        .filter(Article.is_sensitive == True)
        .order_by(desc(Article.published_at))
        .limit(5)
        .all()
    )

    # 10 Berita terbaru
    recent_articles = (
        db.query(Article)
        .order_by(desc(Article.published_at))
        .limit(10)
        .all()
    )

    # Top media
    top_media = (
        db.query(Article.source_name, func.count(Article.id).label("count"))
        .group_by(Article.source_name)
        .order_by(desc("count"))
        .limit(7)
        .all()
    )

    # Top topik
    top_topics = (
        db.query(Article.topic, func.count(Article.id).label("count"))
        .group_by(Article.topic)
        .order_by(desc("count"))
        .limit(6)
        .all()
    )

    # Instagram stats
    total_ig_posts = db.query(IgMedia).count()
    total_ig_comments = db.query(IgComment).count()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "total_articles": total_articles,
            "total_positive": total_positive,
            "total_neutral": total_neutral,
            "total_negative": total_negative,
            "total_sensitive": total_sensitive,
            "sensitive_articles": sensitive_articles,
            "recent_articles": recent_articles,
            "top_media": top_media,
            "top_topics": top_topics,
            "total_ig_posts": total_ig_posts,
            "total_ig_comments": total_ig_comments,
        },
    )


@router.get("/articles", response_class=HTMLResponse)
def articles_table(
    request: Request,
    q: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    sensitive: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Halaman tabel rekap berita dengan filter lengkap (Modul 2)."""
    query = db.query(Article)

    if q:
        query = query.filter(Article.title.ilike(f"%{q}%"))
    if sentiment and sentiment != "all":
        query = query.filter(Article.sentiment == sentiment)
    if sensitive == "yes":
        query = query.filter(Article.is_sensitive == True)
    elif sensitive == "no":
        query = query.filter(Article.is_sensitive == False)
    if topic and topic != "all":
        query = query.filter(Article.topic == topic)

    articles = query.order_by(desc(Article.published_at)).limit(200).all()

    return templates.TemplateResponse(
        request=request,
        name="articles.html",
        context={
            "articles": articles,
            "q": q or "",
            "selected_sentiment": sentiment or "all",
            "selected_sensitive": sensitive or "all",
            "selected_topic": topic or "all",
        },
    )


@router.post("/articles/{article_id}/verify")
def verify_article_label(
    article_id: int,
    sentiment: str = Form(...),
    is_sensitive: bool = Form(False),
    sensitive_category: Optional[str] = Form(None),
    reason: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Koreksi manual label oleh manusia dengan audit trail (Modul 13)."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if article:
        # Catat di audit log
        log = AuditLog(
            article_id=article.id,
            action="koreksi_manual",
            old_value=f"sentimen={article.sentiment}, sensitif={article.is_sensitive}",
            new_value=f"sentimen={sentiment}, sensitif={is_sensitive}",
            user_identifier="admin",
            reason=reason or "Verifikasi manual reviewer kampus",
        )
        db.add(log)

        article.sentiment = sentiment
        article.is_sensitive = is_sensitive
        article.sensitive_category = sensitive_category if is_sensitive else None
        article.is_verified = True
        article.verified_by = "admin"
        article.verified_at = datetime.utcnow()
        db.commit()

    return RedirectResponse(url="/articles", status_code=303)


@router.get("/export/excel")
def export_excel(db: Session = Depends(get_db)):
    """Ekspor rekap berita ke file Excel (.xlsx)."""
    articles = db.query(Article).order_by(desc(Article.published_at)).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rekap Berita UIN Kudus"

    headers = [
        "ID", "Tanggal", "Media", "Judul Berita", "URL",
        "Sentimen", "Skor Sentimen", "Alasan Sentimen",
        "Sensitif?", "Kategori Sensitif", "Alasan Sensitif", "Topik", "Ringkasan"
    ]
    ws.append(headers)

    for a in articles:
        ws.append([
            a.id,
            a.published_at.strftime("%Y-%m-%d %H:%M") if a.published_at else "",
            a.source_name,
            a.title,
            a.url,
            a.sentiment,
            a.sentiment_score,
            a.sentiment_reason,
            "Ya" if a.is_sensitive else "Tidak",
            a.sensitive_category or "",
            a.sensitive_reason or "",
            a.topic or "",
            a.summary or "",
        ])

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)

    filename = f"rekap_monitoring_uin_kudus_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/instagram", response_class=HTMLResponse)
def instagram_view(request: Request, db: Session = Depends(get_db)):
    """Halaman khusus Instagram @uinsunankudus_ (Modul 7)."""
    posts = db.query(IgMedia).order_by(desc(IgMedia.timestamp)).limit(30).all()
    comments = db.query(IgComment).order_by(desc(IgComment.timestamp)).limit(30).all()

    return templates.TemplateResponse(
        request=request,
        name="instagram.html",
        context={
            "posts": posts,
            "comments": comments,
        },
    )


@router.post("/crawl/trigger")
def trigger_crawl(keyword: str = Form("UIN Sunan Kudus"), max_items: int = Form(5), db: Session = Depends(get_db)):
    """Memicu crawling manual dari web dashboard."""
    count = run_pipeline_for_keyword(db, keyword, max_articles=max_items)
    return RedirectResponse(url=f"/articles?crawled={count}", status_code=303)


@router.post("/instagram/sync")
def sync_instagram(db: Session = Depends(get_db)):
    """Sinkronisasi postingan & komentar terbaru Instagram dari API."""
    posts_data = fetch_recent_posts(limit=15)
    for p in posts_data:
        media_id = p.get("id")
        existing = db.query(IgMedia).filter(IgMedia.id == media_id).first()
        ts_str = p.get("timestamp")
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")) if ts_str else datetime.utcnow()

        if not existing:
            media = IgMedia(
                id=media_id,
                caption=p.get("caption"),
                media_type=p.get("media_type"),
                media_url=p.get("media_url"),
                permalink=p.get("permalink"),
                timestamp=ts,
                like_count=p.get("like_count", 0),
                comments_count=p.get("comments_count", 0),
            )
            db.add(media)
        else:
            existing.like_count = p.get("like_count", 0)
            existing.comments_count = p.get("comments_count", 0)

        # Ambil komentar jika ada
        if p.get("comments_count", 0) > 0:
            comments_data = fetch_post_comments(media_id, limit=20)
            for c in comments_data:
                cid = c.get("id")
                c_exist = db.query(IgComment).filter(IgComment.id == cid).first()
                if not c_exist:
                    c_ts_str = c.get("timestamp")
                    c_ts = datetime.fromisoformat(c_ts_str.replace("Z", "+00:00")) if c_ts_str else datetime.utcnow()
                    comment = IgComment(
                        id=cid,
                        media_id=media_id,
                        text=c.get("text", ""),
                        timestamp=c_ts,
                        username=c.get("username"),
                    )
                    db.add(comment)

    db.commit()
    return RedirectResponse(url="/instagram", status_code=303)
