# SUKU-Monitor: Sistem Monitoring Publikasi & Opini Media UIN Sunan Kudus

Sistem monitoring publikasi media online, Google News, dan Instagram resmi **UIN Sunan Kudus** dengan pendekatan **netral, objektif, dan akademis**.

---

## Fitur Utama

1. **Pemantau Berita Otomatis (Google News & Media Online)**
   - Mendeteksi penyebutan UIN Sunan Kudus, IAIN Kudus, STAIN Kudus, rektor/pimpinan, dan PMB.
   - Ekstraksi teks artikel bersih via `trafilatura`.
   - Klasifikasi otomatis sentimen (positif, netral, negatif) & flag isu sensitif (SARA, kekerasan seksual, demonstrasi/anarkis) dengan **Gemini 3.8 Flash** dan cadangan *rule-based*.
   - Setiap penilaian disertai **alasan ringkas** dan **kutipan isi berita** secara transparan.

2. **Integrasi Instagram Kampus Resmi (`@uinsunankudus_`)**
   - Menarik postingan resmi, likes, jumlah komentar via **Meta Graph API**.
   - Menarik komentar warganet untuk analisis sentimen & aspirasi publik terhadap kampus.

3. **Dashboard Web Interaktif**
   - Ringkasan metrik: total berita, sentimen polaritas, alert isu sensitif, grafik distribusi sentimen (Chart.js), dan top media yang sering memberitakan.
   - Tabel rekap lengkap dengan filter kata kunci, sentimen, dan status sensitif.
   - Fitur audit & verifikasi manusia untuk mengoreksi label yang salah.
   - **Ekspor laporan lengkap ke Excel (.xlsx)** dengan satu klik.

---

## Struktur Direktori

```text
├── app/
│   ├── config.py             # Konfigurasi aplikasi dari .env
│   ├── main.py               # Aplikasi FastAPI & lifespan
│   ├── pipeline.py           # Orkestrator crawling & klasifikasi
│   ├── classifiers/
│   │   └── gemini_classifier.py  # Analisis sentimen via Gemini 3.8 Flash & Rules
│   ├── crawlers/
│   │   ├── google_news.py    # Pencarian RSS Google News
│   │   ├── article_extractor.py # Ekstraktor teks via trafilatura
│   │   └── instagram_api.py  # Integrasi Meta Graph API
│   ├── models/
│   │   ├── database.py       # Engine & Session database SQLAlchemy
│   │   └── entities.py       # Tabel articles, ig_media, ig_comments, keywords, audit_logs
│   ├── data/
│   │   └── sources.py        # Daftar portal lokal Jateng, Kemenag, dan PTKIN
│   ├── routers/
│   │   └── web.py            # Endpoint dashboard, tabel rekap, ekspor Excel, Instagram sync
│   └── templates/
│       ├── base.html         # Layout Tailwind CSS
│       ├── dashboard.html    # Halaman utama ringkasan & grafik
│       ├── articles.html     # Rekap tabel berita & verifikasi
│       └── instagram.html    # Halaman pantau Instagram kampus
├── .env.example              # Template variabel konfigurasi (aman untuk git)
├── .gitignore                # Mencegah file rahasia (.env, .db) terunggah ke repo
├── requirements.txt          # Daftar paket Python
├── run.py                    # Entrypoint server uvicorn
└── README.md                 # Dokumentasi ini
```

---

## Cara Menjalankan

### 1. Persiapan Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Konfigurasi `.env`
Salin template `.env.example` ke `.env`:
```bash
cp .env.example .env
```
Isi variabel dengan kredensial Anda:
- `GEMINI_API_KEY`: API key dari Google AI Studio
- `IG_ACCOUNT_ID` & `IG_ACCESS_TOKEN`: dari Meta for Developers

### 3. Menjalankan Server Web
```bash
python3 run.py
```
Akses di peramban: `http://localhost:8000`

---

## Keamanan Data
- File `.env` dan database `suku_monitor.db` **dikecualikan dari Git** melalui `.gitignore`.
- Kredensial rahasia tidak pernah di-commit ke repositori publik.
