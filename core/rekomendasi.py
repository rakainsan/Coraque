def get_rekomendasi(oc_score: float, event_lag1: float,
                    rolling_mean_3: float) -> dict:
    """
    Threshold berbasis distribusi score produksi nyata (scan empiris):
    Range anomali nyata : -0.027 s/d -1.35
    Ringan : -0.027 ≤ score < 0
    Sedang : -0.460 ≤ score < -0.027
    Berat  : score < -0.460
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


    # ── RINGAN (-0.027 ≤ score < 0) ──────────────────────────────────
    if oc_score >= -0.0270:
        if tipe == "drop":
            # Drop ringan — volume sedikit di bawah normal, cukup pantau
            return {
                "tipe"         : "drop",
                "severity"     : "peringatan",
                "emoji"        : "🔻",
                "tindakan"     : "Volume limbah sedikit di bawah pola normal. "
                                 "Pantau kondisi sistem dan konfirmasi jadwal produksi.",
                "bahan_kimia"  : [],
                "infrastruktur": [
                    {
                        "nama"    : "Pemantauan",
                        "tindakan": "Konfirmasi jadwal produksi hari ini. "
                                    "Cek apakah ada libur atau pengurangan produksi."
                    }
                ]
            }
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
                    "lokasi": "Bak 4",
                    "alasan": "Beban TSS meningkat proporsional terhadap "
                              "kenaikan volume limbah"
                              "(Zaimaturahmi, 2023)"
                },
                {
                    "nama"  : "PAC (Poly Aluminium Chloride)",
                    "dosis" : "Tambah 10–15% dari dosis operasional normal",
                    "lokasi": "Bak 3 — Sedimentasi",
                    "alasan": "Flokulasi lebih efektif menangani partikel "
                              "tersuspensi tambahan "
                              "(Radityaningrum & Caroline, 2017)"
                }
            ],
            "infrastruktur": []
        }

    # ── SEDANG (-0.460 ≤ score < -0.027) ─────────────────────────────
    elif oc_score >= -0.460:
        if tipe == "drop":
            return {
                "tipe"         : "drop",
                "severity"     : "peringatan",
                "emoji"        : "🔻",
                "tindakan"     : "Volume limbah jauh di bawah pola normal. \n Lakukan inspeksi fisik sistem IPAL dan \n periksa kondisi sensor water level bak 1.",
                "bahan_kimia"  : [],
                "infrastruktur": [
                    {
                        "nama"    : "Inspeksi Sistem",
                        "tindakan": "1. Periksa kondisi sensor water level bak 1. \n 2. Periksa kebocoran pipa dan sambungan antar bak. \n 3. Konfirmasi jadwal produksi termasuk hari libur atau tanggal merah."
                    }
                ]
            }
        return {
            "tipe"         : "spike",
            "severity"     : "sedang",
            "emoji"        : "🚨",
            "tindakan"     : "Volume limbah signifikan di atas normal. "
                             "Gunakan kombinasi PAC dan Tawas untuk "
                             "mengoptimalkan proses elektrokoagulasi-flokulasi.",
            "bahan_kimia"  : [
                {
                    "nama"  : "PAC (Poly Aluminium Chloride)",
                    "dosis" : "50 mg/L",
                    "lokasi": "Bak 3 — Sedimentasi",
                    "alasan": "PAC membentuk flok lebih cepat dari Tawas "
                              "saat hydraulic retention time memendek "
                              "(Radityaningrum & Caroline, 2017)"
                },
                {
                    "nama"  : "Tawas Al₂(SO₄)₃",
                    "dosis" : "150 mg/L",
                    "lokasi": "Bak 4 dan 3 — Sedimentasi",
                    "alasan": "Kombinasi PAC + Tawas optimal untuk "
                              "penurunan warna limbah batik (Zaimaturahmi, 2023)"
                }
            ],
            "infrastruktur": []
        }

    # ── BERAT (score < -0.460) ────────────────────────────────────────
    else:
        if tipe == "drop":
            return {
                "tipe"         : "drop",
                "severity"     : "peringatan",
                "emoji"        : "🔻",
                "tindakan"     : "Volume limbah sangat jauh di bawah normal. "
                                 "Kemungkinan terjadi gangguan serius pada sistem. "
                                 "Lakukan inspeksi menyeluruh segera.",
                "bahan_kimia"  : [],
                "infrastruktur": [
                    {
                        "nama"    : "Inspeksi Darurat",
                        "tindakan": "1. Periksa kondisi sensor water level bak 1. \n 2. Periksa kebocoran pipa dan sambungan antar bak. \n 3. Konfirmasi jadwal produksi. \n 4. Hubungi teknisi jika sensor tidak merespons."
                    }
                ]
            }
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
                              "(Radityaningrum, 2017)"
                },
                {
                    "nama"  : "Tawas Al₂(SO₄)₃",
                    "dosis" : "150 mg/L",
                    "lokasi": "Bak 4",
                    "alasan": "Netralisasi pH output dan koagulasi sekunder "
                              "(Zaimaturahmi, 2023)"
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
