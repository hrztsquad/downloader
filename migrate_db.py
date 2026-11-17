import sqlite3
import os

db_path = "suku_monitor.db"
if not os.path.exists(db_path):
    print("Database file belum ada, tidak perlu migrasi.")
    exit(0)

conn = sqlite3.connect(db_path)
c = conn.cursor()

# 1. Tambahkan kolom lecturer_name ke tabel articles jika belum ada
try:
    c.execute("ALTER TABLE articles ADD COLUMN lecturer_name VARCHAR(200)")
    print("[OK] Kolom 'lecturer_name' berhasil ditambahkan ke tabel articles.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("[INFO] Kolom 'lecturer_name' sudah ada.")
    else:
        print("[WARN]", e)

# 2. Buat tabel lecturers jika belum ada
c.execute("""
CREATE TABLE IF NOT EXISTS lecturers (
    id INTEGER PRIMARY KEY,
    full_name VARCHAR(250) UNIQUE NOT NULL,
    clean_name VARCHAR(200) NOT NULL,
    alias VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# 3. Buat index jika belum ada
try:
    c.execute("CREATE INDEX IF NOT EXISTS ix_articles_lecturer_name ON articles (lecturer_name)")
    c.execute("CREATE INDEX IF NOT EXISTS ix_lecturers_clean_name ON lecturers (clean_name)")
    conn.commit()
    print("[OK] Index database berhasil diverifikasi.")
except Exception as e:
    print("[WARN] Index error:", e)

conn.close()
print("Migrasi database SQLite selesai 100%.")
