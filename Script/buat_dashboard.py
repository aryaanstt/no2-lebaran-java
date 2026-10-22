"""
Menyusun data dasbor interaktif di folder docs/ (GitHub Pages).

Membaca berkas mentah yang sama dengan analisis_no2_lebaran.py, menghitung ulang
anomali tiap wilayah tiap tahun dengan rumus yang sama, menyederhanakan poligon
supaya halaman tetap ringan, lalu menulis docs/data.js. Halaman docs/index.html
tinggal membaca berkas itu, jadi dasbor dapat dibuka langsung dari disk tanpa
server.

Sebelum menulis, setiap angka dicocokkan dengan Data/02_olahan
(ringkasan_angka.json, anomali_gabungan_117_wilayah.csv, TL_1, TL_2, TL_5).
Kalau ada yang tidak sama, skrip berhenti dengan pesan galat.

    python Script/buat_dashboard.py

Arya Perdana Putra Nasution / 12822007 / Meteorologi ITB
"""

import json
import os
from decimal import Decimal, ROUND_HALF_UP
import numpy as np
import pandas as pd
from scipy import stats

# --------------------------------------------------------------- pengaturan
HERE = os.path.dirname(os.path.abspath(__file__))
AKAR = os.path.abspath(os.path.join(HERE, ".."))
MENTAH = os.path.join(AKAR, "Data", "01_mentah")
OLAHAN = os.path.join(AKAR, "Data", "02_olahan")
DOCS = os.path.join(AKAR, "docs")
os.makedirs(DOCS, exist_ok=True)

TAHUN = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
IDUL = {2019: "2019-06-05", 2020: "2020-05-24", 2021: "2021-05-13",
        2022: "2022-05-02", 2023: "2023-04-22", 2024: "2024-04-10",
        2025: "2025-03-31"}
PERIODE = {"gab": ("Combined", "H−7 to H+7"),
           "mudik": ("Homecoming", "H−7 to H0"),
           "balik": ("Return", "H+1 to H+7")}
E5 = 1e5                 # kolom NO2 disajikan dalam 1e-5 mol/m2
TOLERANSI = 0.0015       # derajat, kira-kira 165 m; tak terlihat pada skala Pulau Jawa
DESIMAL = 3              # pembulatan koordinat, kira-kira 110 m
NAMA_PROVINSI = {"Dki Jakarta": "DKI Jakarta",
                 "Daerah Istimewa Yogyakarta": "DI Yogyakarta"}


# ------------------------------------------------------------------- muat
NO2 = pd.read_csv(os.path.join(MENTAH, "v11_NO2_perKabupaten_500m.csv"))
NO2["wilayah"] = NO2["ADM2_NAME"].str.strip()
NO2["provinsi"] = NO2["ADM1_NAME"].str.strip()
DKI = pd.read_csv(os.path.join(MENTAH, "v18_NO2_Periode_DKI.csv"))
DKI = DKI[DKI["wilayah"].str.strip() == "DKI Jakarta"].iloc[0]


# ------------------------------------------ anomali, sama dengan skrip analisis
def anomali(df, periode):
    """Anomali tiap tahun terhadap acuan tahun itu sendiri, dalam persen."""
    out = pd.DataFrame(
        {t: (df[f"{periode}_{t}"] - df[f"acD_{t}"]) / df[f"acD_{t}"] * 100 for t in TAHUN}
    )
    out.index = df["wilayah"].values
    return out


def wilcoxon_p(nilai):
    """Uji Wilcoxon berperingkat bertanda, dua sisi, sebaran eksak (n = 7)."""
    x = np.asarray([v for v in nilai if np.isfinite(v) and v != 0])
    return float(stats.wilcoxon(x, alternative="two-sided", method="exact").pvalue)


def ringkas(nilai):
    nilai = [float(v) for v in nilai]
    return {"per_tahun": nilai, "rerata": float(np.mean(nilai)),
            "turun": int(sum(v < 0 for v in nilai)), "p": wilcoxon_p(nilai)}


ANOM = {p: anomali(NO2, p) for p in PERIODE}
SEJAWA = {p: ringkas(ANOM[p].mean(axis=0).tolist()) for p in PERIODE}
REGION_RERATA = {p: ANOM[p].mean(axis=1) for p in PERIODE}
NAIK = int((REGION_RERATA["gab"] > 0).sum())


def kajian(baris):
    return ringkas([(baris[f"gab_{t}"] - baris[f"acD_{t}"]) / baris[f"acD_{t}"] * 100
                    for t in TAHUN])


KAJIAN = {"DKI Jakarta": kajian(DKI),
          "Kota Surabaya": kajian(NO2[NO2["wilayah"] == "Kota Surabaya"].iloc[0])}


# ------------------------------------- cocokkan dengan hasil skrip analisis
def sama(a, b, toleransi=1e-9, pesan=""):
    if not np.allclose(a, b, atol=toleransi, equal_nan=True):
        raise SystemExit(f"tidak cocok dengan Data/02_olahan: {pesan}\n  {a}\n  {b}")


with open(os.path.join(OLAHAN, "ringkasan_angka.json"), encoding="utf8") as f:
    RINGKASAN = json.load(f)

for p in PERIODE:
    acuan = RINGKASAN["sejawa"][p]
    sama(SEJAWA[p]["per_tahun"], acuan["per_tahun"], pesan=f"se-Jawa {p} per tahun")
    sama(SEJAWA[p]["rerata"], acuan["rerata"], pesan=f"se-Jawa {p} rerata")
    sama(SEJAWA[p]["p"], acuan["p"], pesan=f"se-Jawa {p} p")
    assert SEJAWA[p]["turun"] == acuan["turun"], p
for nama, hasil in KAJIAN.items():
    acuan = RINGKASAN["wilayah_kajian"][nama]["gab"]
    sama(hasil["per_tahun"], acuan["per_tahun"], pesan=nama)
    sama([hasil["rerata"], hasil["p"]], [acuan["rerata"], acuan["p"]], pesan=nama)
    assert hasil["turun"] == acuan["turun"], nama

tabel = pd.read_csv(os.path.join(OLAHAN, "anomali_gabungan_117_wilayah.csv")).set_index("wilayah")
tabel = tabel.loc[ANOM["gab"].index]
sama(ANOM["gab"].round(2).values, tabel[[str(t) for t in TAHUN]].values, 1e-6, "tabel 117 wilayah")
sama(REGION_RERATA["gab"].round(2).values, tabel["rerata"].values, 1e-6, "rerata 117 wilayah")

tl1 = pd.read_csv(os.path.join(OLAHAN, "TL_1_perubahan_sejawa_periode.csv"))
sama([round(SEJAWA[p]["rerata"], 2) for p in ["mudik", "balik", "gab"]],
     tl1["rerata_persen"].values, 1e-6, "TL_1")
tl2 = pd.read_csv(os.path.join(OLAHAN, "TL_2_anomali_sejawa_tiap_tahun.csv"))
for p, kolom in [("gab", "anomali_gabungan_persen"), ("mudik", "anomali_mudik_persen"),
                 ("balik", "anomali_balik_persen")]:
    sama(np.round(SEJAWA[p]["per_tahun"], 2), tl2[kolom].values, 1e-6, "TL_2 " + p)
tl5 = pd.read_csv(os.path.join(OLAHAN, "TL_5_peringkat_anomali.csv"))
for _, r in tl5.iterrows():
    sama(round(REGION_RERATA["gab"][r["wilayah"]], 1), r["anomali_persen"], 1e-6, "TL_5 " + r["wilayah"])
assert NAIK == 18, NAIK

# kadar NO2 (mode "NO2 column" di dasbor): rerata acuan dan rerata jendela Lebaran
ARAS = pd.Series(NO2[[f"acD_{t}" for t in TAHUN]].mean(axis=1).values * E5, index=NO2["wilayah"].values)
ARAS_LEBARAN = pd.Series(NO2[[f"gab_{t}" for t in TAHUN]].mean(axis=1).values * E5,
                         index=NO2["wilayah"].values)
for nama in ["Kota Surabaya", "Purbalingga", "Ponorogo"]:
    acuan = RINGKASAN["wilayah_kajian"][nama]
    sama([ARAS[nama], ARAS_LEBARAN[nama]], [acuan["aras"], acuan["aras_lebaran"]], pesan="kadar " + nama)
tl4b = pd.read_csv(os.path.join(OLAHAN, "TL_4b_anggota_kelompok.csv"))
sama(ARAS[tl4b["wilayah"]].round(2).values, tl4b["NO2_hari_biasa"].values, 1e-6, "TL_4b kadar hari biasa")
t41 = pd.read_csv(os.path.join(OLAHAN, "T4_1_perubahan_empat_wilayah.csv")).set_index("wilayah")
for nama in ["Kota Surabaya", "Purbalingga", "Ponorogo"]:
    sama(round(ARAS[nama], 2), t41.loc[nama, "NO2_hari_biasa_1e-5_mol_m2"], 1e-6, "T4_1 " + nama)

print("cocok dengan Data/02_olahan: se-Jawa %.2f persen, %d dari 7 tahun turun, p %.4f, %d wilayah naik, "
      "kadar NO2 hari biasa %d wilayah"
      % (SEJAWA["gab"]["rerata"], SEJAWA["gab"]["turun"], SEJAWA["gab"]["p"], NAIK, len(tl4b)))


# -------------------------------------------------- penyederhanaan poligon
def rdp(titik, toleransi):
    """Douglas-Peucker untuk satu cincin; titik pertama dan terakhir dipertahankan."""
    n = len(titik)
    simpan = np.zeros(n, dtype=bool)
    simpan[0] = simpan[-1] = True
    tumpuk = [(0, n - 1)]
    while tumpuk:
        a, b = tumpuk.pop()
        if b <= a + 1:
            continue
        p, q, tengah = titik[a], titik[b], titik[a + 1:b]
        d = q - p
        panjang = np.hypot(d[0], d[1])
        if panjang == 0:
            jarak = np.hypot(tengah[:, 0] - p[0], tengah[:, 1] - p[1])
        else:
            jarak = np.abs(d[0] * (tengah[:, 1] - p[1]) - d[1] * (tengah[:, 0] - p[0])) / panjang
        i = int(np.argmax(jarak))
        if jarak[i] > toleransi:
            k = a + 1 + i
            simpan[k] = True
            tumpuk += [(a, k), (k, b)]
    return titik[simpan]


def luas_bertanda(cincin):
    x, y = cincin[:, 0], cincin[:, 1]
    return 0.5 * np.sum(x[:-1] * y[1:] - x[1:] * y[:-1])


def sederhanakan_cincin(cincin, luar):
    titik = rdp(np.asarray(cincin, dtype=float), TOLERANSI).round(DESIMAL)
    # buang titik berurutan yang jadi kembar sesudah dibulatkan
    beda = np.r_[True, np.any(np.diff(titik, axis=0) != 0, axis=1)]
    titik = titik[beda]
    if len(titik) < 4:
        return None
    # cincin luar searah jarum jam, lubang berlawanan: urutan yang dipakai d3-geo
    if (luas_bertanda(titik) > 0) == luar:
        titik = titik[::-1]
    return titik.tolist()


def poligon_dari_geometri(geom):
    jenis = geom["type"]
    if jenis == "Polygon":
        return [geom["coordinates"]]
    if jenis == "MultiPolygon":
        return geom["coordinates"]
    if jenis == "GeometryCollection":
        keluar = []
        for g in geom["geometries"]:
            keluar += poligon_dari_geometri(g)
        return keluar
    return []


def sederhanakan(geom):
    hasil = []
    for bagian in poligon_dari_geometri(geom):
        luar = sederhanakan_cincin(bagian[0], luar=True)
        if luar is None:
            continue
        lubang = [c for c in (sederhanakan_cincin(c, luar=False) for c in bagian[1:]) if c]
        hasil.append([luar] + lubang)
    return {"type": "MultiPolygon", "coordinates": hasil}


fitur, kotak, titik_awal, titik_akhir = [], [], 0, 0
for _, r in NO2.iterrows():
    geom = json.loads(r[".geo"])
    titik_awal += sum(len(c) for b in poligon_dari_geometri(geom) for c in b)
    sederhana = sederhanakan(geom)
    titik_akhir += sum(len(c) for b in sederhana["coordinates"] for c in b)
    fitur.append({"type": "Feature", "id": r["wilayah"], "properties": {}, "geometry": sederhana})
    # kotak batas tiap wilayah, dipakai dasbor untuk memperbesar peta ke wilayah terpilih
    semua = np.array([xy for b in sederhana["coordinates"] for c in b for xy in c])
    kotak.append(semua.min(axis=0).tolist() + semua.max(axis=0).tolist())
print("titik poligon: %d menjadi %d" % (titik_awal, titik_akhir))

# garis batas provinsi, cukup sebagai garis lon/lat yang dipisah null
with open(os.path.join(MENTAH, "v5_Batas_Provinsi_Jawa.geojson"), encoding="utf8") as f:
    _prov = json.load(f)
garis_lon, garis_lat = [], []
for f_ in _prov["features"]:
    for bagian in poligon_dari_geometri(f_["geometry"]):
        for cincin in bagian:
            titik = rdp(np.asarray(cincin, dtype=float), TOLERANSI * 2).round(DESIMAL)
            if len(titik) < 4:
                continue
            garis_lon += titik[:, 0].tolist() + [None]
            garis_lat += titik[:, 1].tolist() + [None]


# ------------------------------------------------------------- susun data
def bulat(nilai, d):
    """Pembulatan untuk JSON; NaN menjadi null."""
    return [None if not np.isfinite(v) else round(float(v), d) for v in nilai]


def teks_p(p):
    """Nilai p empat desimal, dibulatkan ke atas pada angka 5 seperti di naskah (0,03125 -> 0,0313)."""
    return str(Decimal(repr(p)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


nilai = {}
for p in PERIODE:
    acuan = NO2[[f"acD_{t}" for t in TAHUN]].values * E5
    lebaran = NO2[[f"{p}_{t}" for t in TAHUN]].values * E5
    nilai[p] = {
        "anom": [bulat(baris, 2) for baris in ANOM[p].values],
        "acuan": [bulat(baris, 3) for baris in acuan],
        "lebaran": [bulat(baris, 3) for baris in lebaran],
        # rerata tujuh tahun: rerata anomali tahunan, bukan anomali dari rerata
        "anom_rerata": bulat(REGION_RERATA[p].values, 2),
        "acuan_rerata": bulat(np.nanmean(acuan, axis=1), 3),
        "lebaran_rerata": bulat(np.nanmean(lebaran, axis=1), 3),
    }

DATA = {
    "tahun": TAHUN,
    "idul_fitri": [IDUL[t] for t in TAHUN],
    "periode": {p: {"nama": n, "jendela": j} for p, (n, j) in PERIODE.items()},
    "wilayah": NO2["wilayah"].tolist(),
    "provinsi": [NAMA_PROVINSI.get(p, p) for p in NO2["provinsi"]],
    "kotak": kotak,      # [bujur min, lintang min, bujur maks, lintang maks] tiap wilayah
    "nilai": nilai,
    "sejawa": {p: {"per_tahun": bulat(SEJAWA[p]["per_tahun"], 2),
                   "rerata": round(SEJAWA[p]["rerata"], 2),
                   "turun": SEJAWA[p]["turun"], "p": teks_p(SEJAWA[p]["p"])}
               for p in PERIODE},
    "angka_utama": {
        "sejawa_gab": round(SEJAWA["gab"]["rerata"], 2),
        "tahun_turun": SEJAWA["gab"]["turun"],
        "p_sejawa": teks_p(SEJAWA["gab"]["p"]),
        "wilayah_naik": NAIK,
        "jumlah_wilayah": len(NO2),
        "dki": round(KAJIAN["DKI Jakarta"]["rerata"], 1),
        "dki_turun": KAJIAN["DKI Jakarta"]["turun"],
        "dki_p": teks_p(KAJIAN["DKI Jakarta"]["p"]),
        "surabaya": round(KAJIAN["Kota Surabaya"]["rerata"], 1),
        "surabaya_turun": KAJIAN["Kota Surabaya"]["turun"],
        "surabaya_p": teks_p(KAJIAN["Kota Surabaya"]["p"]),
    },
    "geojson": {"type": "FeatureCollection", "features": fitur},
    "batas_provinsi": {"lon": garis_lon, "lat": garis_lat},
}

jalur = os.path.join(DOCS, "data.js")
with open(jalur, "w", encoding="utf8", newline="\n") as f:
    f.write("// Dibuat oleh Script/buat_dashboard.py, jangan disunting manual.\n")
    f.write("window.NO2_DATA = ")
    json.dump(DATA, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";\n")
print("ditulis: docs/data.js, %.0f kB" % (os.path.getsize(jalur) / 1024))
