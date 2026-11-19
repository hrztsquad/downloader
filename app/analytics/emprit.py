"""Modul Analisis ala Drone Emprit untuk SUKU-Monitor UIN Sunan Kudus.
Menghasilkan:
1. Net Sentiment Score (NSS) & Sentiment Favorability Index
2. Share of Voice (SoV) Media & Entitas
3. Timeline Tren Pemberitaan (Volume per Waktu berdasar Sentimen)
4. Social Network Analysis (SNA) Graph (Media <-> Dosen <-> Topik)
5. Top Keywords / Word Frequency (dengan filter Stopwords Bahasa Indonesia)
6. Top Figures / Tokoh Paling Banyak Diliput
"""

import re
from collections import Counter
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.models.entities import Article

# Stopwords umum Bahasa Indonesia untuk ekstraksi Word Cloud
ID_STOPWORDS = {
    "yang", "di", "dan", "dari", "ke", "ini", "itu", "untuk", "pada", "adalah",
    "dengan", "sebagai", "dalam", "bisa", "oleh", "akan", "juga", "atau", "tak",
    "ada", "tidak", "tersebut", "dapat", "bagi", "ia", "mereka", "kita", "kami",
    "kamu", "dia", "saat", "setelah", "karena", "lebih", "sudah", "tentang",
    "para", "namun", "sementara", "lalu", "antara", "secara", "hingga", "agar",
    "menjadi", "harus", "banyak", "tahun", "hari", "kali", "serta", "satu", "dua",
    "tiga", "hal", "atas", "bukan", "hanya", "lagi", "seperti", "semua", "bila",
    "saat", "jika", "kini", "sangat", "pun", "belum", "masih", "tentu", "terus",
    "kembali", "usai", "baru", "bahkan", "sejumlah", "menurut", "katanya", "terkait",
    "melalui", "terhadap", "ingin", "punya", "bisa", "agar", "kemudian", "kata",
    "kudus", "uin", "iain", "stain", "sunan" # diexclude jika ingin kata kunci topik spesifik
}


def calculate_emprit_analytics(db: Session) -> Dict[str, Any]:
    """Menghitung metrik analitik komprehensif ala Drone Emprit."""
    articles: List[Article] = db.query(Article).all()
    total_articles = len(articles)

    if total_articles == 0:
        return {
            "total_articles": 0,
            "nss": 0.0,
            "sentiment_counts": {"positif": 0, "netral": 0, "negatif": 0},
            "timeline": {"labels": [], "positif": [], "netral": [], "negatif": []},
            "media_sov": [],
            "entity_sov": [],
            "top_keywords": [],
            "top_figures": [],
            "sna_graph": {"nodes": [], "edges": []},
        }

    # 1. Sentimen & Net Sentiment Score (NSS)
    pos_count = sum(1 for a in articles if a.sentiment == "positif")
    neu_count = sum(1 for a in articles if a.sentiment == "netral")
    neg_count = sum(1 for a in articles if a.sentiment == "negatif")

    # Rumus NSS Drone Emprit: ((Positif - Negatif) / Total) * 100
    nss = round(((pos_count - neg_count) / total_articles) * 100, 1)

    # 2. Timeline Mentions (Bulanan)
    # Kelompokkan berdasarkan YYYY-MM
    monthly_data: Dict[str, Dict[str, int]] = {}
    for a in articles:
        dt = a.published_at or a.crawled_at or datetime.utcnow()
        key = dt.strftime("%Y-%m")
        if key not in monthly_data:
            monthly_data[key] = {"positif": 0, "netral": 0, "negatif": 0}
        sent = a.sentiment if a.sentiment in ["positif", "netral", "negatif"] else "netral"
        monthly_data[key][sent] += 1

    sorted_months = sorted(monthly_data.keys())
    # Batasi 12 bulan terakhir jika panjang
    if len(sorted_months) > 12:
        sorted_months = sorted_months[-12:]

    timeline = {
        "labels": sorted_months,
        "positif": [monthly_data[m]["positif"] for m in sorted_months],
        "netral": [monthly_data[m]["netral"] for m in sorted_months],
        "negatif": [monthly_data[m]["negatif"] for m in sorted_months],
    }

    # 3. Share of Voice (SoV) - Media
    media_counts = Counter(a.source_name for a in articles if a.source_name)
    top_media_list = media_counts.most_common(10)
    other_media_count = sum(count for media, count in media_counts.items() if media not in dict(top_media_list))
    
    media_sov = [
        {"name": media, "count": count, "percent": round((count / total_articles) * 100, 1)}
        for media, count in top_media_list
    ]
    if other_media_count > 0:
        media_sov.append({
            "name": "Media Lainnya",
            "count": other_media_count,
            "percent": round((other_media_count / total_articles) * 100, 1),
        })

    # 4. Share of Voice (SoV) - Entitas Brand (UIN vs IAIN vs STAIN vs Tokoh)
    uin_count = sum(1 for a in articles if "uin" in (a.title or "").lower())
    iain_count = sum(1 for a in articles if "iain" in (a.title or "").lower())
    stain_count = sum(1 for a in articles if "stain" in (a.title or "").lower())
    dosen_count = sum(1 for a in articles if a.lecturer_name)

    entity_sov = [
        {"name": "UIN Sunan Kudus", "count": uin_count},
        {"name": "IAIN Kudus", "count": iain_count},
        {"name": "STAIN Kudus", "count": stain_count},
        {"name": "Dosen / Tokoh Disebut", "count": dosen_count},
    ]

    # 5. Top Keywords / Word Cloud Extraction
    all_words: List[str] = []
    for a in articles:
        if not a.title:
            continue
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", a.title.lower())
        tokens = cleaned.split()
        for t in tokens:
            if len(t) >= 4 and t not in ID_STOPWORDS and not t.isdigit():
                all_words.append(t.capitalize())

    word_counter = Counter(all_words)
    top_keywords = [{"word": word, "count": count} for word, count in word_counter.most_common(25)]

    # 6. Top Figures / Tokoh Paling Banyak Diberitakan
    lecturer_counter = Counter(a.lecturer_name for a in articles if a.lecturer_name)
    top_figures = []
    for name, total in lecturer_counter.most_common(8):
        pos = sum(1 for a in articles if a.lecturer_name == name and a.sentiment == "positif")
        neu = sum(1 for a in articles if a.lecturer_name == name and a.sentiment == "netral")
        neg = sum(1 for a in articles if a.lecturer_name == name and a.sentiment == "negatif")
        top_figures.append({
            "name": name,
            "total": total,
            "positif": pos,
            "netral": neu,
            "negatif": neg,
        })

    # 7. Social Network Analysis (SNA) Graph Data
    # Nodes: Media (kategori 'media'), Dosen/Tokoh (kategori 'person'), Topik (kategori 'topic')
    # Edges: Hubungan Media -> Dosen, Media -> Topik, Dosen -> Topik
    nodes_map: Dict[str, Dict[str, Any]] = {}
    edges_counter: Counter = Counter()

    for a in articles:
        media_node_id = f"m_{a.source_name}"
        if media_node_id not in nodes_map and a.source_name:
            nodes_map[media_node_id] = {
                "id": media_node_id,
                "label": a.source_name,
                "group": "media",
                "value": 1,
            }
        elif media_node_id in nodes_map:
            nodes_map[media_node_id]["value"] += 1

        # Hubungan dengan Dosen
        if a.lecturer_name:
            person_node_id = f"p_{a.lecturer_name}"
            if person_node_id not in nodes_map:
                nodes_map[person_node_id] = {
                    "id": person_node_id,
                    "label": a.lecturer_name,
                    "group": "person",
                    "value": 1,
                }
            else:
                nodes_map[person_node_id]["value"] += 1

            if a.source_name:
                edges_counter[(media_node_id, person_node_id)] += 1

        # Hubungan dengan Topik
        if a.topic and a.topic != "lainnya":
            topic_label = a.topic.replace("_", " ").title()
            topic_node_id = f"t_{a.topic}"
            if topic_node_id not in nodes_map:
                nodes_map[topic_node_id] = {
                    "id": topic_node_id,
                    "label": topic_label,
                    "group": "topic",
                    "value": 1,
                }
            else:
                nodes_map[topic_node_id]["value"] += 1

            if a.source_name:
                edges_counter[(media_node_id, topic_node_id)] += 1
            if a.lecturer_name:
                edges_counter[(f"p_{a.lecturer_name}", topic_node_id)] += 1

    # Ambil nodes teratas agar graf tetap rapi dan performant
    top_nodes = sorted(nodes_map.values(), key=lambda x: x["value"], reverse=True)[:35]
    top_node_ids = {n["id"] for n in top_nodes}

    edges_list = [
        {"from": src, "to": dst, "value": count}
        for (src, dst), count in edges_counter.items()
        if src in top_node_ids and dst in top_node_ids
    ]

    return {
        "total_articles": total_articles,
        "nss": nss,
        "sentiment_counts": {
            "positif": pos_count,
            "netral": neu_count,
            "negatif": neg_count,
        },
        "timeline": timeline,
        "media_sov": media_sov,
        "entity_sov": entity_sov,
        "top_keywords": top_keywords,
        "top_figures": top_figures,
        "sna_graph": {
            "nodes": top_nodes,
            "edges": edges_list,
        },
    }
