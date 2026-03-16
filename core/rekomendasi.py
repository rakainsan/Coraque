def get_rekomendasi(oc_score: float, event_lag1: float,
                    rolling_mean_3: float) -> dict:
    """
    Threshold berbasis distribusi score produksi nyata (scan empiris):
    Range anomali nyata : -0.027 s/d -1.35
    Ringan : -0.027 ≤ score < 0       (lag1 ~30–32)
    Sedang : -0.460 ≤ score < -0.027  (lag1 ~33–34)
    Berat  : score < -0.460           (lag1 ≥35)
    """
    tipe = "spike" if event_lag1 >= rolling_mean_3 else "drop"

    # ── NORMAL ────────────────────────────────────────────────────────
    if oc_score >= 0:
        return {
            "tipe"         : "normal",
            "severity"     : "normal",
            "emoji"        : "✅",
            "tindakan"     : "Kondisi volume limbah normal. "
                             "Tidak diperlukan tindakan khusus.",
            "bahan_kimia"  : [],
            "infrastruktur": []
        }

    # ── DROP ──────────────────────────────────────────────────────────
    if tipe == "drop":
        return {
            "tipe"         : "drop",
            "severity"     : "peringatan",
            "emoji"        : "🔻",
            "tindakan"     : "Volume limbah jauh di bawah pola normal. "
                             "Lakukan inspeksi fisik sistem IPAL dan "
                             "periksa kondisi sensor water level bak 1.",
            "bahan_kimia"  : [],
            "infrastruktur": [
                {
                    "nama"    : "Inspeksi Sistem",
                    "tindakan": "1. Periksa kondisi sensor water level bak 1. "
                                "2. Periksa kebocoran pipa dan sambungan antar bak. "
                                "3. Konfirmasi jadwal produksi termasuk hari libur "
                                "atau tanggal merah."
                }
            ]
        }

    # ── SPIKE RINGAN  (-0.027 ≤ score < 0) ──────────────────────────
    if oc_score >= -0.0270:
        return {
            "tipe"         : "spike",
            "severity"     : "ringan",
            "emoji"        : "⚠️",
            "tindakan"     : "Volume limbah sedikit di atas pola normal. "
                             "Tingkatkan dosis koagulan secara proporsional.",
            "bahan_kimia"  : [
                {
                    "nama"  : "Tawas Al₂(SO₄)₃",
                    "dosis" : "Tambah 10–15% dari dosis operasional normal",
                    "lokasi": "Bak 3 — Sedimentasi",
                    "alasan": "Beban TSS meningkat proporsional terhadap "
                              "kenaikan volume limbah (Zaimaturahmi, 2023)"
                },
                {
                    "nama"  : "PAC (Poly Aluminium Chloride)",
                    "dosis" : "Tambah 10–15% dari dosis operasional normal",
                    "lokasi": "Bak 3 — Sedimentasi",
                    "alasan": "Flokulasi lebih efektif menangani partikel "
                              "tersuspensi tambahan "
                              
                }
            ],
            "infrastruktur": []
        }

    # ── SPIKE SEDANG  (-0.460 ≤ score < -0.027) ────────────────────
    elif oc_score >= -0.460:
        return {
            "tipe"         : "spike",
            "severity"     : "sedang",
            "emoji"        : "🚨",
            "tindakan"     : "Volume limbah signifikan di atas normal. "
                             "Gunakan kombinasi PAC dan Tawas untuk "
                             "mengoptimalkan proses koagulasi-flokulasi.",
            "bahan_kimia"  : [
                {
                    "nama"  : "PAC (Poly Aluminium Chloride)",
                    "dosis" : "50 mg/L",
                    "lokasi": "Bak 3 — Sedimentasi",
                    "alasan": "PAC membentuk flok lebih cepat dari Tawas "
                              "saat hydraulic retention time memendek "
                              
                },
                {
                    "nama"  : "Tawas Al₂(SO₄)₃",
                    "dosis" : "150 mg/L",
                    "lokasi": "Bak 4 dan 3 — Netralisasi Sedimentasi",
                    "alasan": "Kombinasi PAC + Tawas optimal untuk "
                              "penurunan warna limbah batik "
                              
                }
            ],
            "infrastruktur": []
        }

    # ── SPIKE BERAT  (score < -0.460) ───────────────────────────────
    else:
        return {
            "tipe"         : "spike",
            "severity"     : "berat",
            "emoji"        : "🆘",
            "tindakan"     : "Volume limbah jauh melampaui kapasitas normal IPAL. "
                             "Aktifkan pengolahan intensif dengan dosis koagulan "
                             "tinggi dan aktifkan bak ekualisasi sebelum "
                             "limbah masuk bak 1.",
            "bahan_kimia"  : [
                {
                    "nama"  : "PAC (Poly Aluminium Chloride)",
                    "dosis" : "75–100 mg/L",
                    "lokasi": "Bak 3 — Sedimentasi",
                    "alasan": "Dosis tinggi untuk tangani beban organik ekstrem "
                              
                },
                {
                    "nama"  : "Tawas Al₂(SO₄)₃",
                    "dosis" : "150 mg/L",
                    "lokasi": "Bak 4 — Netralisasi",
                    "alasan": "Netralisasi pH output dan koagulasi sekunder "
                              
                }
            ],
            "infrastruktur": [
                {
                    "nama"    : "Bak Ekualisasi (Equalization Tank)",
                    "tindakan": "Tampung sementara kelebihan volume limbah di "
                                "bak ekualisasi sebelum inlet bak 1. Alirkan "
                                "secara bertahap ke IPAL agar laju aliran masuk "
                                "tetap stabil dan tidak melebihi kapasitas "
                                "pengolahan per siklus. Untuk skala UMKM dapat "
                                "menggunakan drum plastik 200L sebagai bak "
                                "ekualisasi darurat."
                },
                {
                    "nama"    : "Keputusan Produksi",
                    "tindakan": "Rencanakan jadwal produksi bergilir — bagi "
                                "batch produksi menjadi dua sesi hari itu dan "
                                "keesokan harinya serta menambah jam operasional "
                                "IPAL untuk mengimbangi peningkatan volume limbah."
                }
            ]
        }