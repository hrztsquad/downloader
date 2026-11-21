"""Deteksi isu berita & saran tindak lanjut berbasis data (rule-based, tanpa API eksternal)."""

from collections import Counter
from datetime import datetime, timedelta

# key: (label, kata kunci, rekomendasi dasar per sentimen)
ISSUES = {
    "moderasi_beragama": ("Moderasi Beragama", ["moderasi beragama", "toleransi", "radikal", "intoleran", "ekstrem", "kerukunan", "keberagaman", "lintas agama"],
        {"negatif": "Koordinasikan Rumah Moderasi Beragama dan Humas untuk menerbitkan klarifikasi resmi berbasis fakta; hindari polemik di kolom komentar dan libatkan tokoh agama kampus sebagai juru bicara.",
         "netral": "Pantau perkembangan isu dan siapkan narasi moderasi beragama (kajian, dialog lintas iman) sebagai konten edukatif proaktif.",
         "positif": "Perkuat dan amplifikasi program moderasi beragama melalui kanal resmi serta jalin kolaborasi dengan media yang memberitakan."}),
    "sara_sensitif": ("SARA / Isu Sensitif", ["sara", "penistaan", "hoaks", "hoax", "provokasi", "ujaran kebencian", "fitnah"],
        {"negatif": "Aktifkan protokol manajemen krisis: verifikasi fakta, klarifikasi tertulis dalam 24 jam, dan koordinasi dengan pimpinan serta pihak berwenang bila perlu.",
         "netral": "Lakukan pemantauan intensif dan siapkan pernyataan siaga.",
         "positif": "Dokumentasikan sebagai bahan literasi media."}),
    "kekerasan_seksual": ("Kekerasan Seksual / Etik", ["pelecehan", "kekerasan seksual", "asusila", "perundungan", "bullying", "cabul"],
        {"negatif": "Aktifkan Satgas PPKS, pastikan perlindungan korban dan proses etik transparan, serta sampaikan perkembangan penanganan secara berkala tanpa membuka identitas.",
         "netral": "Tinjau efektivitas kanal pelaporan dan sosialisasi PPKS.",
         "positif": "Publikasikan capaian pencegahan kekerasan seksual di kampus."}),
    "demo_aksi": ("Aksi Mahasiswa / Demonstrasi", ["demo", "unjuk rasa", "aksi mahasiswa", "protes", "tuntutan", "audiensi"],
        {"negatif": "Buka ruang dialog dengan perwakilan mahasiswa (BEM/DEMA), tanggapi tuntutan secara tertulis dan tetapkan tenggat tindak lanjut yang jelas.",
         "netral": "Pantau agenda aksi dan siapkan juru bicara.",
         "positif": "Tampilkan dialog konstruktif sebagai praktik tata kelola yang baik."}),
    "hukum_integritas": ("Hukum & Integritas", ["korupsi", "gratifikasi", "tersangka", "kpk", "kejaksaan", "pungli", "plagiat", "ijazah palsu"],
        {"negatif": "Libatkan unit hukum dan Inspektorat; sampaikan sikap institusi, hormati asas praduga tak bersalah, dan perbaiki kontrol internal terkait.",
         "netral": "Pantau proses hukum dan siapkan bahan klarifikasi.",
         "positif": "Publikasikan komitmen integritas dan zona integritas."}),
    "layanan_kritik": ("Layanan & Kritik Publik", ["ukt", "biaya kuliah", "keluhan", "pelayanan", "fasilitas", "kritik", "mengeluh", "parkir", "wifi", "beasiswa"],
        {"negatif": "Petakan keluhan berulang, tetapkan unit penanggung jawab dan tanggapi publik lewat kanal resmi dengan batas waktu respons.",
         "netral": "Kumpulkan masukan sebagai bahan evaluasi layanan.",
         "positif": "Pertahankan kualitas layanan dan sebarkan praktik baik."}),
    "pmb_promosi": ("PMB & Promosi", ["pmb", "penerimaan mahasiswa", "pendaftaran", "jalur mandiri", "snbp", "snbt", "umptkin", "maba"],
        {"negatif": "Perjelas informasi pendaftaran dan tanggapi kebingungan calon mahasiswa di kanal resmi.",
         "netral": "Optimalkan publikasi jadwal dan alur pendaftaran melalui media yang dominan memberitakan.",
         "positif": "Dorong konten PMB tambahan pada media berkinerja baik untuk memperluas jangkauan."}),
    "prestasi_akademik": ("Prestasi & Reputasi Akademik", ["prestasi", "juara", "penghargaan", "akreditasi", "guru besar", "profesor", "wisuda", "lulusan", "jurnal", "riset", "penelitian", "publikasi", "scopus", "sinta"],
        {"negatif": "Telaah penyebab penurunan reputasi akademik dan siapkan rencana perbaikan terukur.",
         "netral": "Dorong publikasi capaian lebih aktif.",
         "positif": "Amplifikasi capaian melalui siaran pers, media sosial resmi, dan kemitraan media."}),
    "pengabdian_kkn": ("KKN & Pengabdian", ["kkn", "pengabdian", "desa binaan", "bakti sosial", "kuliah kerja nyata"],
        {"negatif": "Evaluasi pelaksanaan KKN dan komunikasikan perbaikan kepada masyarakat mitra.",
         "netral": "Dokumentasikan kegiatan KKN secara rutin.",
         "positif": "Jadikan dampak KKN sebagai storytelling kemitraan masyarakat."}),
    "kepemimpinan": ("Pimpinan & Kebijakan", ["rektor", "wakil rektor", "dekan", "kebijakan", "pelantikan", "pimpinan", "senat"],
        {"negatif": "Siapkan penjelasan kebijakan yang transparan dan satu pintu komunikasi dari pimpinan.",
         "netral": "Sosialisasikan kebijakan baru secara jelas.",
         "positif": "Perkuat citra kepemimpinan lewat publikasi capaian kebijakan."}),
}
DEFAULT = ("Isu Umum Kelembagaan", {"negatif": "Lakukan klarifikasi dan monitoring lanjutan.",
           "netral": "Lanjutkan pemantauan rutin.", "positif": "Pertahankan dan publikasikan secara berkelanjutan."})


def detect_issue(article):
    text = f"{article.title or ''} {article.sensitive_category or ''} {(article.content or '')[:1500]}".lower()
    title = (article.title or "").lower()
    best, score = None, 0
    for key, (_, kws, _r) in ISSUES.items():
        s = sum((3 if k in title else 1) for k in kws if k in text)
        if s > score:
            best, score = key, s
    return best


def build_followups(articles, now=None):
    """Kelompokkan artikel per isu, hitung data pendukung, hasilkan saran."""
    now = now or datetime.utcnow()
    groups = {}
    for a in articles:
        key = detect_issue(a) or "lainnya"
        groups.setdefault(key, []).append(a)

    result = []
    for key, items in groups.items():
        label = ISSUES[key][0] if key in ISSUES else DEFAULT[0]
        recs = ISSUES[key][2] if key in ISSUES else DEFAULT[1]
        sent = Counter((i.sentiment or "netral") for i in items)
        total = len(items)
        neg_pct = round(sent["negatif"] / total * 100)
        dominant = "negatif" if sent["negatif"] >= max(sent["positif"], sent["netral"]) and sent["negatif"] else \
            ("positif" if sent["positif"] >= sent["netral"] else "netral")
        recent = sum(1 for i in items if i.published_at and i.published_at >= now - timedelta(days=7))
        prev = sum(1 for i in items if i.published_at and now - timedelta(days=14) <= i.published_at < now - timedelta(days=7))
        trend = "meningkat" if recent > prev else ("menurun" if recent < prev else "stabil")
        media = Counter(i.source_name for i in items if i.source_name).most_common(3)
        if neg_pct >= 40 or key in ("sara_sensitif", "kekerasan_seksual", "hukum_integritas") and sent["negatif"]:
            priority = "Tinggi"
        elif neg_pct >= 20 or recent >= 3:
            priority = "Sedang"
        else:
            priority = "Rendah"
        evidence = (f"{total} berita (positif {sent['positif']}, netral {sent['netral']}, negatif {sent['negatif']}; "
                    f"{neg_pct}% negatif). Tren 7 hari terakhir {trend} ({recent} vs {prev} pekan sebelumnya). "
                    + (f"Media dominan: {', '.join(f'{m} ({c})' for m, c in media)}." if media else ""))
        for i in items:
            i.issue_label = label
            i.issue_advice = recs.get(i.sentiment or "netral", recs["netral"])
        result.append({"key": key, "label": label, "total": total, "sentiment": dict(sent), "neg_pct": neg_pct,
                       "dominant": dominant, "trend": trend, "priority": priority, "evidence": evidence,
                       "recommendation": recs[dominant], "articles": sorted(items, key=lambda x: x.published_at or datetime.min, reverse=True)})
    order = {"Tinggi": 0, "Sedang": 1, "Rendah": 2}
    result.sort(key=lambda g: (order[g["priority"]], -g["total"]))
    return result
