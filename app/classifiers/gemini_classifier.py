"""Modul klasifikasi berita menggunakan Gemini API (gemini-3.8-flash) & fallback rule-based."""

import json
from typing import Dict, Any
from google import genai
from google.genai import types
from app.config import settings

# Inisialisasi client Gemini
client = None
if settings.gemini_api_key:
    try:
        client = genai.Client(api_key=settings.gemini_api_key)
    except Exception as e:
        print(f"[WARN] Gagal inisialisasi Gemini client: {e}")


PROMPT_SYSTEM = """Anda adalah analis sentimen dan pemantau isu media yang netral, objektif, dan akademis.
Tugas Anda adalah menganalisis berita/postingan mengenai UIN Sunan Kudus (atau IAIN/STAIN Kudus).

PRINSIP NETRALITAS:
- Jangan membela atau menyudutkan kampus.
- Nilai fakta secara objektif berdasarkan kalimat yang tertulis.
- Jelaskan alasan secara ringkas dan transparan.

TENTUKAN 4 HAL:
1. SENTIMEN terhadap UIN Sunan Kudus:
   - "positif": prestasi, akreditasi, kerja sama, capaian, kontribusi positif.
   - "netral": pengumuman, pelantikan rutin, berita informatif biasa, atau kampus hanya disebut sambil lalu.
   - "negatif": korupsi, kritik kebijakan, keluhan pelayanan, penurunan performa, sanksi.

2. SCORE SENTIMEN: angka antara -1.0 (sangat negatif) sampai +1.0 (sangat positif). Netral di sekitar 0.0.

3. FLAG SENSITIF (terpisah dari sentimen):
   - is_sensitive: true jika berita memuat isu berisiko tinggi.
   - sensitive_category: salah satu dari ["sara", "kekerasan_seksual", "demo", "anarkis", "narkoba", "korupsi", "lainnya"] atau null jika false.
   - sensitive_reason: alasan singkat jika sensitif.

4. TOPIK UTAMA: salah satu dari ["pmb", "akademik", "prestasi", "tata_kelola", "kemahasiswaan", "kerjasama", "hukum_kriminal", "keagamaan", "lainnya"].
5. RINGKASAN: 1-2 kalimat ringkasan faktual isi berita.

OUTPUT HARUS BERUPA JSON VALID dengan struktur:
{
  "sentiment": "positif" | "netral" | "negatif",
  "sentiment_score": float,
  "sentiment_reason": "alasan singkat",
  "is_sensitive": boolean,
  "sensitive_category": string | null,
  "sensitive_reason": string | null,
  "topic": string,
  "summary": "ringkasan 1-2 kalimat"
}
"""


def classify_with_rules(title: str, content: str) -> Dict[str, Any]:
    """Fallback berbasis aturan kata kunci jika API Gemini bermasalah atau kuota habis."""
    text = f"{title} {content}".lower()

    # Rule sensitif
    is_sensitive = False
    sensitive_category = None
    sensitive_reason = None

    if any(k in text for k in ["pelecehan seksual", "kekerasan seksual", "pemerkosaan", "pencabulan"]):
        is_sensitive = True
        sensitive_category = "kekerasan_seksual"
        sensitive_reason = "Teks memuat indikasi isu kekerasan/pelecehan seksual"
    elif any(k in text for k in ["sara", "penistaan agama", "intoleran", "rasisme"]):
        is_sensitive = True
        sensitive_category = "sara"
        sensitive_reason = "Teks memuat indikasi isu SARA / intoleransi"
    elif any(k in text for k in ["demo", "unjuk rasa", "aksi massa", "anarkis", "bentrok"]):
        is_sensitive = True
        sensitive_category = "demo"
        sensitive_reason = "Teks memuat liputan demonstrasi / aksi massa"

    # Rule sentimen dasar
    positif_kw = ["prestasi", "juara", "akreditasi unggul", "meraih", "penghargaan", "sukses", "kerjasama", "inovasi"]
    negatif_kw = ["korupsi", "ditangkap", "tersangka", "kasus", "sanksi", "kecewa", "ricuh", "protes", "polemik"]

    pos_count = sum(1 for k in positif_kw if k in text)
    neg_count = sum(1 for k in negatif_kw if k in text)

    if neg_count > pos_count and neg_count > 0:
        sentiment = "negatif"
        score = -0.6
        reason = f"Ditemukan indikasi kata bernada negatif ({neg_count} kata kunci)"
    elif pos_count > neg_count and pos_count > 0:
        sentiment = "positif"
        score = 0.6
        reason = f"Ditemukan indikasi kata bernada positif ({pos_count} kata kunci)"
    else:
        sentiment = "netral"
        score = 0.0
        reason = "Berita informatif / tidak dominan sentimen polar (rule-based)"

    topic = "lainnya"
    if any(k in text for k in ["pmb", "span-ptkin", "um-ptkin", "pendaftaran mahasiswa", "calon mahasiswa"]):
        topic = "pmb"
    elif any(k in text for k in ["wisuda", "kuliah", "fakultas", "prodi", "kurikulum"]):
        topic = "akademik"
    elif any(k in text for k in ["juara", "prestasi", "lomba", "medali"]):
        topic = "prestasi"

    return {
        "sentiment": sentiment,
        "sentiment_score": score,
        "sentiment_reason": reason + " [klasifikasi fallback]",
        "is_sensitive": is_sensitive,
        "sensitive_category": sensitive_category,
        "sensitive_reason": sensitive_reason,
        "topic": topic,
        "summary": title[:200],
    }


def classify_article(title: str, content: str) -> Dict[str, Any]:
    """Klasifikasi artikel menggunakan Gemini 3.8 Flash, dengan fallback ke rule-based."""
    if not client or not settings.gemini_api_key:
        return classify_with_rules(title, content)

    # Potong konten agar hemat token (maks 3000 karakter cukup untuk sentimen & topik)
    content_snippet = content[:3000] if content else title

    prompt = f"JUDUL: {title}\n\nISI ARTIKEL:\n{content_snippet}"

    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=PROMPT_SYSTEM,
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )

        parsed = json.loads(response.text)
        return parsed

    except Exception as e:
        print(f"[WARN] Gemini API gagal ({e}), beralih ke rule-based.")
        return classify_with_rules(title, content)
