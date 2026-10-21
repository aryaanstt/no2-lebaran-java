"""
Analisis NO2 troposferik Pulau Jawa selama periode Lebaran 2019-2025.

Membaca berkas hasil ekspor Google Earth Engine di folder Data/01_mentah,
menghitung seluruh angka yang dipakai di naskah, lalu menggambar ulang gambar
Bab 4 dan Lampiran. Notebook analisis_no2_lebaran.ipynb dan berkas .py ini
berisi langkah yang sama, tinggal pilih mana yang lebih enak dijalankan.

Arya Perdana Putra Nasution / 12822007 / Meteorologi ITB
"""

import json
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch
from matplotlib.collections import PatchCollection
from matplotlib.colors import TwoSlopeNorm, Normalize
from scipy import stats

# --------------------------------------------------------------- pengaturan
HERE = os.path.dirname(os.path.abspath(__file__))
AKAR = os.path.abspath(os.path.join(HERE, ".."))
MENTAH = os.path.join(AKAR, "Data", "01_mentah")
OLAHAN = os.path.join(AKAR, "Data", "02_olahan")
GAMBAR = os.path.join(AKAR, "Gambar")
os.makedirs(OLAHAN, exist_ok=True)
os.makedirs(GAMBAR, exist_ok=True)

TAHUN = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
IDUL = {2019: "2019-06-05", 2020: "2020-05-24", 2021: "2021-05-13",
        2022: "2022-05-02", 2023: "2023-04-22", 2024: "2024-04-10",
        2025: "2025-03-31"}
WILAYAH_KAJIAN = ["DKI Jakarta", "Kota Surabaya", "Purbalingga", "Ponorogo"]
E5 = 1e5                      # kolom NO2 disajikan dalam 1e-5 mol/m2
JENDELA = (-7, 7)             # H-7 sampai H+7
ACUAN_AWAL = range(-60, -30)  # H-60 sampai H-31
ACUAN_AKHIR = range(30, 60)   # H+30 sampai H+59

# warna dipakai seragam di semua gambar
BIRU, JINGGA, HIJAU, MERAH = "#0072B2", "#D55E00", "#009E73", "#C0392B"
TINTA, TINTA2, KISI = "#000000", "#000000", "#DDDDDD"
LAUT, KOSONG = "#CBD9E3", "#E7ECEF"
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9.5,
    "axes.titlesize": 9.5,
    "axes.labelsize": 9.5,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.fontsize": 8.5,
    "axes.edgecolor": TINTA2,
    "axes.labelcolor": TINTA,
    "text.color": TINTA,
    "xtick.color": TINTA2,
    "ytick.color": TINTA2,
    "figure.dpi": 130,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})


TAMPILKAN = False      # di notebook diubah menjadi True supaya gambarnya ikut tampil
JUDUL = False          # judul gambar cukup di kapsi naskah; ubah ke True untuk melihat judulnya
LEBAR = 5.5            # inci, selebar bidang tulis naskah (14 cm), dicetak tanpa diperkecil


def koma(teks):
    """Desimal memakai koma dan tanda minus yang benar, sesuai kaidah penulisan naskah."""
    return str(teks).replace(".", ",").replace("-", "\u2212")


def _sumbu_koma(fig):
    from matplotlib.ticker import ScalarFormatter, FuncFormatter
    for ax in fig.axes:
        for sumbu in (ax.xaxis, ax.yaxis):
            if isinstance(sumbu.get_major_formatter(), ScalarFormatter):
                sumbu.set_major_formatter(FuncFormatter(lambda v, pos: koma("%g" % v)))


def simpan(fig, nama):
    _sumbu_koma(fig)
    jalur = os.path.join(GAMBAR, nama)
    fig.savefig(jalur, facecolor="white")
    print("  gambar:", nama)
    if TAMPILKAN:
        plt.show()
    else:
        plt.close(fig)
    return jalur


def geser(tanggal, n):
    return (pd.Timestamp(tanggal) + pd.Timedelta(days=n)).strftime("%Y-%m-%d")


# ------------------------------------------------------------------- muat
def muat_periode(nama_berkas):
    """Tabel per kabupaten/kota: nilai tiap periode tiap tahun, plus poligonnya."""
    df = pd.read_csv(os.path.join(MENTAH, nama_berkas))
    df["wilayah"] = df["ADM2_NAME"].str.strip()
    df["provinsi"] = df["ADM1_NAME"].str.strip()
    return df


def muat_harian(nama_berkas, kosong_jadi_nol=False):
    df = pd.read_csv(os.path.join(MENTAH, nama_berkas))
    df["tanggal"] = df["tanggal"].str.strip()
    df["wilayah"] = df["wilayah"].str.strip()
    if kosong_jadi_nol:
        # sel kosong pada berkas hujan berarti hari tanpa hujan, bukan data hilang
        df["nilai"] = df["nilai"].fillna(0.0)
    return df.dropna(subset=["nilai"])


NO2 = muat_periode("v11_NO2_perKabupaten_500m.csv")
HUJ = muat_periode("v11_Hujan_perKabupaten_CHIRPS.csv")
SUH = muat_periode("v11_Suhu_perKabupaten_ERA5Land.csv")
DKI = pd.read_csv(os.path.join(MENTAH, "v18_NO2_Periode_DKI.csv"))
BULANAN = pd.read_csv(os.path.join(MENTAH, "v16_NO2_Bulanan_perKabupaten.csv"))
ISPU = pd.read_csv(os.path.join(MENTAH, "v14_ISPU_DKIJakarta_2022.csv"))

def siapkan_harian():
    """Gabungkan deret harian tiga wilayah kajian dengan deret DKI Jakarta.

    Berkas v13 memuat Kota Surabaya, Purbalingga, Ponorogo, dan Kota Jakarta
    Timur. Sejak bimbingan 15 September, DKI Jakarta dipakai utuh satu provinsi,
    jadi Kota Jakarta Timur diganti oleh deret DKI pada berkas v18. Hasilnya
    disimpan di Data/02_olahan supaya langkah berikutnya tinggal membacanya.
    """
    dki = pd.read_csv(os.path.join(MENTAH, "v18_Harian_DKI.csv"))
    dki = dki[dki["wilayah"].str.strip() == "DKI Jakarta"]
    keluar = {}
    for kunci, kolom, kosong_nol, faktor in [("NO2", "no2", False, E5),
                                             ("Hujan", "hujan", True, 1.0),
                                             ("Suhu", "suhu", False, 1.0)]:
        lama = muat_harian(f"v13_Harian_{kunci}.csv", kosong_jadi_nol=kosong_nol)
        lama = lama[lama["wilayah"] != "Kota Jakarta Timur"]
        baru = pd.DataFrame({"tanggal": dki["tanggal"].astype(str).str.strip(),
                             "wilayah": "DKI Jakarta",
                             "nilai": dki[kolom] * faktor})
        if kosong_nol:
            baru["nilai"] = baru["nilai"].fillna(0.0)
        gabung = pd.concat([lama, baru], ignore_index=True).dropna(subset=["nilai"])
        gabung.to_csv(os.path.join(OLAHAN, f"harian_{kunci.lower()}.csv"),
                      index=False, encoding="utf-8-sig")
        keluar[kunci] = gabung
    return keluar


HARIAN_MENTAH = siapkan_harian()
H_NO2, H_HUJ, H_SUH = HARIAN_MENTAH["NO2"], HARIAN_MENTAH["Hujan"], HARIAN_MENTAH["Suhu"]

print("wilayah pada tabel periode:", len(NO2), "| baris NO2 harian:", len(H_NO2))


# ---------------------------------------------------- anomali per wilayah
def anomali(df, periode="gab"):
    """Anomali tiap tahun terhadap acuan tahun itu sendiri, dalam persen."""
    out = pd.DataFrame(
        {t: (df[f"{periode}_{t}"] - df[f"acD_{t}"]) / df[f"acD_{t}"] * 100 for t in TAHUN}
    )
    out.index = df["wilayah"].values
    return out


ANOM = {p: anomali(NO2, p) for p in ["mudik", "balik", "gab"]}
ARAS = pd.Series((NO2[[f"acD_{t}" for t in TAHUN]].mean(axis=1) * E5).values,
                 index=NO2["wilayah"].values)          # kadar hari biasa, 1e-5 mol/m2
ARAS_LEBARAN = pd.Series((NO2[[f"gab_{t}" for t in TAHUN]].mean(axis=1) * E5).values,
                         index=NO2["wilayah"].values)

rerata_sejawa = {p: ANOM[p].mean(axis=0) for p in ANOM}           # per tahun
anom_wilayah = ANOM["gab"].mean(axis=1)                           # per wilayah
print("anomali gabungan se-Jawa: %.2f persen | wilayah naik: %d dari %d"
      % (anom_wilayah.mean(), (anom_wilayah > 0).sum(), len(anom_wilayah)))


def wilcoxon_p(nilai):
    """Uji Wilcoxon berperingkat bertanda, dua sisi, sebaran eksak (n = 7)."""
    x = np.asarray([v for v in nilai if np.isfinite(v) and v != 0])
    if len(x) < 1:
        return np.nan
    return stats.wilcoxon(x, alternative="two-sided", method="exact").pvalue


def ringkas(nilai):
    nilai = list(nilai)
    return {"per_tahun": nilai, "rerata": float(np.mean(nilai)),
            "turun": int(sum(v < 0 for v in nilai)), "p": float(wilcoxon_p(nilai))}


# empat wilayah kajian: DKI Jakarta dipakai utuh satu provinsi (berkas v18),
# tiga sisanya langsung dari tabel 117 wilayah
def baris_wilayah(nama):
    if nama == "DKI Jakarta":
        return DKI[DKI["wilayah"].str.strip() == "DKI Jakarta"].iloc[0]
    return NO2[NO2["wilayah"] == nama].iloc[0]


KAJIAN = {}
for nama in WILAYAH_KAJIAN:
    r = baris_wilayah(nama)
    KAJIAN[nama] = {
        "aras": float(np.mean([r[f"acD_{t}"] for t in TAHUN]) * E5),
        "aras_lebaran": float(np.mean([r[f"gab_{t}"] for t in TAHUN]) * E5),
    }
    for p in ["mudik", "balik", "gab"]:
        KAJIAN[nama][p] = ringkas([(r[f"{p}_{t}"] - r[f"acD_{t}"]) / r[f"acD_{t}"] * 100
                                   for t in TAHUN])

print("\nempat wilayah kajian (periode gabungan)")
for nama in WILAYAH_KAJIAN:
    g = KAJIAN[nama]["gab"]
    print("  %-14s aras %5.2f | %6.1f persen | turun %d dari 7 | p %.4f"
          % (nama, KAJIAN[nama]["aras"], g["rerata"], g["turun"], g["p"]))

SEJAWA = {p: ringkas(rerata_sejawa[p].tolist()) for p in ["mudik", "balik", "gab"]}
print("se-Jawa gabungan: %.2f persen | turun %d dari 7 | p %.4f"
      % (SEJAWA["gab"]["rerata"], SEJAWA["gab"]["turun"], SEJAWA["gab"]["p"]))


# ------------------------------------------------------------ data harian
def deret_harian(nama):
    """Anomali NO2, curah hujan, dan suhu tiap hari H-7..H+7 pada satu wilayah.

    Acuan harian dihitung dari berkas harian yang sama, yaitu rerata H-60..H-31
    dan H+30..H+59 pada tahun yang bersangkutan, supaya sebanding dengan peta.
    """
    no2 = dict(zip(H_NO2.loc[H_NO2["wilayah"] == nama, "tanggal"],
                   H_NO2.loc[H_NO2["wilayah"] == nama, "nilai"]))
    huj = dict(zip(H_HUJ.loc[H_HUJ["wilayah"] == nama, "tanggal"],
                   H_HUJ.loc[H_HUJ["wilayah"] == nama, "nilai"]))
    suh = dict(zip(H_SUH.loc[H_SUH["wilayah"] == nama, "tanggal"],
                   H_SUH.loc[H_SUH["wilayah"] == nama, "nilai"]))
    kumpul = {d: {"an": [], "huj": [], "suh": []} for d in range(JENDELA[0], JENDELA[1] + 1)}
    titik_huj, titik_suh = [], []
    for t in TAHUN:
        acu = [no2[geser(IDUL[t], d)] for d in list(ACUAN_AWAL) + list(ACUAN_AKHIR)
               if geser(IDUL[t], d) in no2]
        if not acu:
            continue
        A = float(np.mean(acu))
        if not np.isfinite(A) or A <= 0:
            continue
        for d in range(JENDELA[0], JENDELA[1] + 1):
            tg = geser(IDUL[t], d)
            if tg in huj:
                kumpul[d]["huj"].append(huj[tg])
            if tg in suh:
                kumpul[d]["suh"].append(suh[tg])
            if tg not in no2:
                continue
            an = (no2[tg] - A) / A * 100
            kumpul[d]["an"].append(an)
            if tg in huj:
                titik_huj.append((huj[tg], an))
            if tg in suh:
                titik_suh.append((suh[tg], an))
    tabel = pd.DataFrame({
        "hari": list(range(JENDELA[0], JENDELA[1] + 1)),
        "anomali": [np.mean(kumpul[d]["an"]) if kumpul[d]["an"] else np.nan
                    for d in range(JENDELA[0], JENDELA[1] + 1)],
        "hujan": [np.mean(kumpul[d]["huj"]) if kumpul[d]["huj"] else np.nan
                  for d in range(JENDELA[0], JENDELA[1] + 1)],
        "suhu": [np.mean(kumpul[d]["suh"]) if kumpul[d]["suh"] else np.nan
                 for d in range(JENDELA[0], JENDELA[1] + 1)],
    })
    return tabel, np.array(titik_huj), np.array(titik_suh)


HARIAN, TITIK = {}, {}
for nama in WILAYAH_KAJIAN:
    tabel, th, ts = deret_harian(nama)
    HARIAN[nama] = tabel
    TITIK[nama] = {"hujan": th, "suhu": ts}


def korelasi(x, y):
    r, p = stats.pearsonr(x, y)
    return {"r": float(r), "p": float(p), "n": int(len(x))}


KOR = {nama: {"hujan": korelasi(TITIK[nama]["hujan"][:, 0], TITIK[nama]["hujan"][:, 1]),
              "suhu": korelasi(TITIK[nama]["suhu"][:, 0], TITIK[nama]["suhu"][:, 1])}
       for nama in WILAYAH_KAJIAN}

print("\nkorelasi antarhari (anomali NO2 terhadap cuaca harian)")
for nama in WILAYAH_KAJIAN:
    print("  %-14s hujan r %6.3f p %.3f n %3d | suhu r %6.3f p %.3f n %3d"
          % (nama, KOR[nama]["hujan"]["r"], KOR[nama]["hujan"]["p"], KOR[nama]["hujan"]["n"],
             KOR[nama]["suhu"]["r"], KOR[nama]["suhu"]["p"], KOR[nama]["suhu"]["n"]))


# --------------------------------------------- keterkaitan antarwilayah
def selisih_cuaca(df):
    """Selisih rerata periode gabungan terhadap acuan, dalam satuan aslinya."""
    s = pd.DataFrame({t: df[f"gab_{t}"] - df[f"acD_{t}"] for t in TAHUN})
    s.index = df["wilayah"].values
    return s.mean(axis=1)


D_HUJAN = selisih_cuaca(HUJ)
D_SUHU = selisih_cuaca(SUH)
sejajar = anom_wilayah.index
KOR_JAWA = {
    "hujan": korelasi(D_HUJAN[sejajar].values, anom_wilayah.values),
    "suhu": korelasi(D_SUHU[sejajar].values, anom_wilayah.values),
}
print("antarwilayah se-Jawa: hujan r %.3f p %.3f | suhu r %.3f p %.3f (r2 %.1f persen)"
      % (KOR_JAWA["hujan"]["r"], KOR_JAWA["hujan"]["p"], KOR_JAWA["suhu"]["r"],
         KOR_JAWA["suhu"]["p"], KOR_JAWA["suhu"]["r"] ** 2 * 100))
print("rerata selisih: hujan %+.2f mm/hari | suhu %+.2f derajat"
      % (D_HUJAN.mean(), D_SUHU.mean()))


# ------------------------------------- pembanding dengan ISPU DKI Jakarta
ispu = ISPU[["tanggal", "no2"]].dropna()
ispu["tanggal"] = ispu["tanggal"].astype(str).str.strip()
sat = H_NO2[H_NO2["wilayah"] == "DKI Jakarta"][["tanggal", "nilai"]]
PASANG = ispu.merge(sat, on="tanggal", how="inner").rename(columns={"nilai": "satelit"})
rs, ps = stats.spearmanr(PASANG["no2"], PASANG["satelit"])
rp, pp = stats.pearsonr(PASANG["no2"], PASANG["satelit"])
ISPU_HASIL = {"n": len(PASANG), "spearman": float(rs), "p_spearman": float(ps),
              "pearson": float(rp), "p_pearson": float(pp)}
print("ISPU DKI 2022: n %d | Spearman %.3f (p %.4f) | Pearson %.3f"
      % (ISPU_HASIL["n"], rs, ps, rp))


# ------------------------------------ dua kelompok wilayah (kuartil aras)
# penggolongan memakai kolom acA, yaitu kadar acuan tahunan tiap wilayah
ARAS_KUARTIL = pd.Series((NO2["acA"] * E5).values, index=NO2["wilayah"].values)
Q1, Q3 = ARAS_KUARTIL.quantile(0.25), ARAS_KUARTIL.quantile(0.75)
ARAS_K = ARAS_KUARTIL
is_kota = pd.Series([n.startswith("Kota ") for n in ARAS.index], index=ARAS.index)
KEL_ASAL = ARAS_K[(ARAS_K >= Q3) & is_kota].index.tolist()
KEL_TUJUAN = ARAS_K[(ARAS_K <= Q1) & (~is_kota)].index.tolist()
print("\nkuartil aras: Q1 %.2f | Q3 %.2f -> kota asal %d, kabupaten tujuan %d"
      % (Q1, Q3, len(KEL_ASAL), len(KEL_TUJUAN)))
print("  kota asal   : %.2f persen" % anom_wilayah[KEL_ASAL].mean())
print("  kab. tujuan : %.2f persen" % anom_wilayah[KEL_TUJUAN].mean())


# =========================================================== mesin peta ==
# Poligon tiap kabupaten dan kota ikut terbawa pada kolom .geo hasil ekspor
# Earth Engine, jadi peta dapat digambar tanpa berkas batas wilayah terpisah.
def cincin_dari_geometri(geom):
    jenis = geom["type"]
    if jenis == "Polygon":
        return [geom["coordinates"]]
    if jenis == "MultiPolygon":
        return geom["coordinates"]
    if jenis == "GeometryCollection":
        keluar = []
        for g in geom["geometries"]:
            keluar += cincin_dari_geometri(g)
        return keluar
    return []


def jalur_wilayah(geo_teks):
    """Satu objek Path matplotlib untuk satu wilayah (bisa banyak pulau)."""
    poligon = cincin_dari_geometri(json.loads(geo_teks))
    titik, kode = [], []
    for bagian in poligon:
        for cincin in bagian:
            if len(cincin) < 3:
                continue
            titik += list(cincin) + [cincin[0]]
            kode += [MplPath.MOVETO] + [MplPath.LINETO] * (len(cincin) - 1) + [MplPath.CLOSEPOLY]
    if not titik:
        return None
    return MplPath(np.array(titik), kode)


JALUR = {r["wilayah"]: jalur_wilayah(r[".geo"]) for _, r in NO2.iterrows()}

with open(os.path.join(MENTAH, "v5_Batas_Provinsi_Jawa.geojson"), encoding="utf8") as f:
    _prov = json.load(f)
JALUR_PROVINSI = [jalur_wilayah(json.dumps(f["geometry"])) for f in _prov["features"]]

BATAS_PETA = (105.0, 114.7, -8.85, -5.75)   # lon kiri, lon kanan, lat bawah, lat atas


def gambar_peta(ax, nilai, vmin, vmax, palet, tengah=None, garis_wilayah=0.25):
    """Warnai tiap kabupaten dan kota menurut nilainya."""
    norm = (TwoSlopeNorm(vmin=vmin, vcenter=tengah, vmax=vmax) if tengah is not None
            else Normalize(vmin=vmin, vmax=vmax))
    cmap = plt.get_cmap(palet)
    tambalan, warna = [], []
    for nama, jalur in JALUR.items():
        if jalur is None:
            continue
        v = nilai.get(nama, np.nan)
        tambalan.append(PathPatch(jalur))
        warna.append(cmap(norm(v)) if np.isfinite(v) else KOSONG)
    ax.set_facecolor(LAUT)
    ax.add_collection(PatchCollection(tambalan, facecolors=warna, edgecolors="white",
                                      linewidths=garis_wilayah, zorder=2))
    for jalur in JALUR_PROVINSI:
        if jalur is not None:
            ax.add_patch(PathPatch(jalur, facecolor="none", edgecolor=TINTA,
                                   linewidth=0.55, zorder=3))
    ax.set_xlim(BATAS_PETA[0], BATAS_PETA[1])
    ax.set_ylim(BATAS_PETA[2], BATAS_PETA[3])
    ax.set_aspect("equal")
    return norm, cmap


def derajat(ax, kecil=False):
    bujur = [106, 112] if kecil else [106, 108, 110, 112, 114]
    ax.set_xticks(bujur)
    lintang = [-8, -6] if kecil else [-8, -7, -6]
    ax.set_yticks(lintang)
    ax.set_xticklabels([f"{v}°BT" for v in bujur],
                       fontsize=7.2 if kecil else 9)
    ax.set_yticklabels([f"{abs(v)}°LS" for v in lintang],
                       fontsize=7.2 if kecil else 9)
    for sisi in ax.spines.values():
        sisi.set_color(TINTA2)
        sisi.set_linewidth(0.6)


def peta_tunggal(nilai, judul, satuan, nama_berkas, palet="YlOrRd",
                 vmin=None, vmax=None, tengah=None, catatan=None, penanda=None):
    vmin = np.nanpercentile(list(nilai.values), 2) if vmin is None else vmin
    vmax = np.nanpercentile(list(nilai.values), 98) if vmax is None else vmax
    fig, ax = plt.subplots(figsize=(LEBAR, 2.9))
    norm, cmap = gambar_peta(ax, nilai, vmin, vmax, palet, tengah)
    derajat(ax)
    if JUDUL:
        ax.set_title(judul, fontsize=11, fontweight="bold", pad=26 if catatan else 10)
    if catatan and JUDUL:
        ax.text(0.5, 1.02, catatan, transform=ax.transAxes, ha="center", va="bottom",
                fontsize=9, color=TINTA2)
    if penanda:
        for nama, (lon, lat, teks, warna, arah) in penanda.items():
            ax.plot(lon, lat, "o", ms=5, mfc="none", mec=warna, mew=1.2, zorder=5)
            ax.annotate(teks, xy=(lon, lat), xytext=(0, arah),
                        textcoords="offset points", ha="center", fontsize=6.5,
                        color=warna, fontweight="bold",
                        bbox=dict(boxstyle="round,pad=0.18", fc="white", ec=warna, lw=0.7),
                        arrowprops=dict(arrowstyle="-", color=warna, lw=0.7), zorder=6)
    bar = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax,
                       orientation="horizontal", fraction=0.045, pad=0.12, aspect=40)
    bar.set_label(satuan, fontsize=8.5)
    bar.outline.set_linewidth(0.5)
    return simpan(fig, nama_berkas)


def peta_banyak(daftar, judul, satuan, nama_berkas, palet="YlOrRd",
                vmin=None, vmax=None, tengah=None, kolom=3):
    """Beberapa petak peta dengan satu skala warna bersama."""
    semua = np.concatenate([s.values.astype(float) for _, s in daftar])
    vmin = np.nanpercentile(semua, 2) if vmin is None else vmin
    vmax = np.nanpercentile(semua, 98) if vmax is None else vmax
    baris = int(np.ceil(len(daftar) / kolom))
    fig, sumbu = plt.subplots(baris, kolom, figsize=(LEBAR, (LEBAR / kolom) * 0.34 * baris + 0.20 * baris + 0.42))
    sumbu = np.atleast_1d(sumbu).ravel()
    for k, (ax, (nama, nilai)) in enumerate(zip(sumbu, daftar)):
        norm, cmap = gambar_peta(ax, nilai, vmin, vmax, palet, tengah, garis_wilayah=0.12)
        derajat(ax, kecil=True)
        if k // kolom < baris - 1:
            ax.set_xticklabels([])
        if k % kolom:
            ax.set_yticklabels([])
        ax.set_title(nama, fontsize=8.5, fontweight="bold", pad=3)
    for ax in sumbu[len(daftar):]:
        ax.axis("off")
    if JUDUL:
        fig.suptitle(judul, fontsize=11, fontweight="bold", y=0.998)
    # skala warna diletakkan pada ruang tersendiri di bawah supaya tidak menutupi label bujur
    tinggi = fig.get_figheight()
    fig.tight_layout(rect=[0, 0, 1, 0.965 if JUDUL else 1.0], h_pad=0.8)
    bawah = min(a.get_position().y0 for a in sumbu[:len(daftar)])
    cax = fig.add_axes([0.2, bawah - 0.40 / tinggi, 0.6, 0.09 / tinggi])
    bar = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax, orientation="horizontal")
    bar.set_label(satuan, fontsize=8.5)
    bar.ax.tick_params(labelsize=7.5)
    return simpan(fig, nama_berkas)


# ----------------------------------------- peta per petak, resolusi 0,01°
# Sebelum dirata-ratakan ke wilayah administratif, NO2 dilihat dulu pada
# resolusi grid aslinya (0,01° atau sekitar 1,1 km). Raster v15 memuat, untuk
# setiap tahun, rerata acuan, gabungan, arus mudik, dan arus balik per petak.
import tifffile

RASTER = tifffile.imread(os.path.join(MENTAH, "v15_Raster_perTahun.tif"))
LON0, LAT0, DXY = 104.99048025385159, -5.590025570235549, 0.010000045742818514
NY, NX = RASTER.shape[:2]
lon_petak = LON0 + (np.arange(NX) + 0.5) * DXY
lat_petak = LAT0 - (np.arange(NY) + 0.5) * DXY
xx, yy = np.meshgrid(lon_petak, lat_petak)
titik_petak = np.column_stack([xx.ravel(), yy.ravel()])
darat = np.zeros(len(titik_petak), dtype=bool)
for jalur in JALUR_PROVINSI:
    if jalur is not None:
        darat |= jalur.contains_points(titik_petak)
DARAT = darat.reshape(NY, NX)


def pita(nama, tahun):
    urutan = {"acD": 0, "gab": 1, "mudik": 2, "balik": 3}[nama]
    return RASTER[..., 4 * TAHUN.index(tahun) + urutan].astype(float)


PETAK_ACUAN = np.nanmean([pita("acD", t) for t in TAHUN], axis=0) * E5
PETAK_LEBARAN = np.nanmean([pita("gab", t) for t in TAHUN], axis=0) * E5
with np.errstate(divide="ignore", invalid="ignore"):
    PETAK_ANOMALI = np.nanmean([np.where(pita("acD", t) > 0,
                                         (pita("gab", t) - pita("acD", t)) / pita("acD", t) * 100,
                                         np.nan) for t in TAHUN], axis=0)
for larik in (PETAK_ACUAN, PETAK_LEBARAN, PETAK_ANOMALI):
    larik[~DARAT] = np.nan
print("petak darat: %d | rerata acuan %.2f | rerata Lebaran %.2f | petak menurun %.1f %%"
      % (DARAT.sum(), np.nanmean(PETAK_ACUAN), np.nanmean(PETAK_LEBARAN),
         np.mean(PETAK_ANOMALI[DARAT & np.isfinite(PETAK_ANOMALI)] < 0) * 100))


def gambar_petak(ax, larik, norm, cmap):
    ax.set_facecolor(LAUT)
    ax.imshow(np.ma.masked_where(~DARAT, np.ones_like(larik)), cmap=matplotlib.colors.ListedColormap([KOSONG]),
              interpolation="nearest", extent=[LON0, LON0 + NX * DXY, LAT0 - NY * DXY, LAT0],
              origin="upper", zorder=1)
    ax.imshow(np.ma.masked_invalid(larik), cmap=cmap, norm=norm, interpolation="nearest",
              extent=[LON0, LON0 + NX * DXY, LAT0 - NY * DXY, LAT0], origin="upper", zorder=2)
    for jalur in JALUR_PROVINSI:
        if jalur is not None:
            ax.add_patch(PathPatch(jalur, facecolor="none", edgecolor=TINTA, linewidth=0.5, zorder=3))
    ax.set_xlim(BATAS_PETA[0], BATAS_PETA[1])
    ax.set_ylim(BATAS_PETA[2], BATAS_PETA[3])
    ax.set_aspect("equal")
    derajat(ax)


def peta_petak(larik, satuan, nama_berkas, vmin, vmax, rerata=None):
    """Peta per petak dengan skala warna berjenjang, seperti peta versi awal."""
    from matplotlib.colors import LogNorm
    norm = LogNorm(vmin=max(vmin, 0.8), vmax=vmax)
    cmap = plt.get_cmap("YlOrRd")
    fig, ax = plt.subplots(figsize=(LEBAR, 2.6))
    gambar_petak(ax, np.where(larik > 0, larik, np.nan), norm, cmap)
    if rerata is not None:
        ax.text(0.985, 0.94, "rerata petak " + koma("%.2f" % rerata), transform=ax.transAxes,
                ha="right", va="top", fontsize=7.5, color=TINTA,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=TINTA2, lw=0.6))
    bar = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax, orientation="horizontal",
                       fraction=0.04, pad=0.13, aspect=45, extend="max",
                       ticks=[1, 2, 4, 8, 15])
    bar.ax.set_xticklabels([koma("%.1f" % v) if v < 10 else koma("%d" % v) for v in [1, 2, 4, 8, 15]])
    bar.ax.tick_params(labelsize=7.5)
    bar.set_label(satuan, fontsize=8.5)
    bar.outline.set_linewidth(0.5)
    return simpan(fig, nama_berkas)


# ------------------------------------------------- Gambar 4.2, 4.3, 4.4, 4.6
gabung_petak = np.concatenate([PETAK_ACUAN[DARAT], PETAK_LEBARAN[DARAT]])
skala_kadar = (0.8, 15.0)
satuan_kadar = "NO$_2$ troposferik ($\\times10^{-5}$ mol/m$^2$)"
peta_petak(PETAK_LEBARAN, satuan_kadar, "G4_02_no2_lebaran.png", *skala_kadar,
           rerata=float(np.nanmean(PETAK_LEBARAN[DARAT])))
peta_petak(PETAK_ACUAN, satuan_kadar, "G4_03_no2_acuan.png", *skala_kadar,
           rerata=float(np.nanmean(PETAK_ACUAN[DARAT])))

# Gambar 4.4: (a) anomali per petak, (b) anomali rerata kabupaten dan kota
BATAS_ANOM = 30
norm_anom = TwoSlopeNorm(vmin=-BATAS_ANOM, vcenter=0, vmax=BATAS_ANOM)
cmap_anom = plt.get_cmap("RdBu_r")
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(LEBAR, 3.9))
gambar_petak(ax1, PETAK_ANOMALI, norm_anom, cmap_anom)
ax1.set_title("(a) resolusi 0,01°", loc="left", fontsize=8.5, fontweight="bold")
ax1.set_xticklabels([])
gambar_peta(ax2, anom_wilayah, -BATAS_ANOM, BATAS_ANOM, "RdBu_r", tengah=0)
derajat(ax2)
ax2.set_title("(b) rerata tiap kabupaten dan kota", loc="left", fontsize=8.5, fontweight="bold")
fig.tight_layout()
bar = fig.colorbar(plt.cm.ScalarMappable(norm=norm_anom, cmap=cmap_anom), ax=[ax1, ax2],
                   orientation="horizontal", fraction=0.035, pad=0.06, aspect=45, extend="both")
bar.set_label("anomali NO$_2$ (%)", fontsize=8.5)
bar.ax.tick_params(labelsize=7.5)
simpan(fig, "G4_04_anomali.png")

anom_min, anom_maks = float(anom_wilayah.min()), float(anom_wilayah.max())

TITIK_KAJIAN = {
    "DKI Jakarta": (106.83, -6.18, "DKI Jakarta −20,5%", BIRU, 26),
    "Kota Surabaya": (112.75, -7.27, "Kota Surabaya −20,7%", BIRU, 24),
    "Purbalingga": (109.36, -7.33, "Purbalingga +5,0%", JINGGA, -24),
    "Ponorogo": (111.47, -7.93, "Ponorogo +2,0%", JINGGA, -24),
}
peta_tunggal(anom_wilayah, "Letak keempat wilayah kajian pada peta anomali",
             "anomali NO$_2$ (%)", "G4_06_wilayah_kajian.png", palet="RdBu_r",
             vmin=anom_min, vmax=anom_maks, tengah=0, penanda=TITIK_KAJIAN)

# --------------------------------------------------------- Gambar L.20
fig, ax = plt.subplots(figsize=(LEBAR, 2.75))
gambar_peta(ax, anom_wilayah, anom_min, anom_maks, "RdBu_r", tengah=0)
for nama in KEL_ASAL:
    ax.add_patch(PathPatch(JALUR[nama], facecolor="none", edgecolor="#154360", lw=1.1, zorder=4))
for nama in KEL_TUJUAN:
    ax.add_patch(PathPatch(JALUR[nama], facecolor="none", edgecolor="#7E3F00", lw=1.1, zorder=4))
derajat(ax)
if JUDUL:
    ax.set_title("Letak kelompok %d kota asal dan %d kabupaten tujuan"
                 % (len(KEL_ASAL), len(KEL_TUJUAN)), fontsize=11, fontweight="bold", pad=10)
ax.plot([], [], color="#154360", lw=2, label="kota asal (kuartil kadar teratas)")
ax.plot([], [], color="#7E3F00", lw=2, label="kabupaten tujuan (kuartil kadar terbawah)")
ax.legend(loc="lower left", fontsize=7.5, frameon=True, framealpha=0.9)
simpan(fig, "L20_kelompok_wilayah.png")


# ==================================================== gambar bukan peta ==
WARNA_KAJIAN = {"DKI Jakarta": "#1F4E79", "Kota Surabaya": "#2CA02C",
                "Purbalingga": JINGGA, "Ponorogo": "#9467BD"}
NAMA_BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
              "Agustus", "September", "Oktober", "November", "Desember"]


def rapikan(ax, judul=None, label_x=None, label_y=None):
    ax.grid(color=KISI, linewidth=0.8)
    ax.set_axisbelow(True)
    for sisi in ["top", "right"]:
        ax.spines[sisi].set_visible(False)
    if judul and JUDUL:
        ax.set_title(judul, fontsize=11, fontweight="bold", pad=8)
    if label_x:
        ax.set_xlabel(label_x)
    if label_y:
        ax.set_ylabel(label_y)


# -------------------------------------------- Gambar 4.1 rerata bulanan
kolom_bulan = [k for k in BULANAN.columns if k.startswith("b20")]
bulanan_wilayah = BULANAN[kolom_bulan] * E5
klim = np.array([bulanan_wilayah[[k for k in kolom_bulan if k.endswith(f"_{b:02d}")]]
                 .mean(axis=1).mean() for b in range(1, 13)])
bulan_idul = sorted({int(IDUL[t][5:7]) for t in TAHUN})
fig, ax = plt.subplots(figsize=(LEBAR, 2.9))
# latar musim: puncak musim hujan dan puncak musim kemarau
ax.axvspan(0.5, 2.5, color="#DCE9F5", zorder=0)
ax.axvspan(11.5, 12.5, color="#DCE9F5", zorder=0)
ax.axvspan(5.5, 8.5, color="#FBE7D2", zorder=0)
ax.text(1.5, 1.0, "Des–Feb\n(puncak musim hujan)", transform=ax.get_xaxis_transform(),
        ha="center", va="bottom", fontsize=6.8, color="#2E6DA4")
ax.text(7.0, 1.0, "Jun–Agu\n(puncak musim kemarau)", transform=ax.get_xaxis_transform(),
        ha="center", va="bottom", fontsize=6.8, color="#B5651D")
ax.plot(range(1, 13), klim, color=BIRU, lw=2, marker="o", ms=5, mfc="white", zorder=3)
ax.plot(bulan_idul, klim[[b - 1 for b in bulan_idul]], "o", color=BIRU, ms=8, zorder=4,
        label="bulan tempat Idul Fitri 2019–2025 jatuh")
for b, v in zip(range(1, 13), klim):
    ax.annotate(koma("%.2f" % v), (b, v), xytext=(0, 7 if b not in (6, 7, 8) else -13),
                textcoords="offset points", ha="center", fontsize=6.8, color=TINTA2)
ax.axhline(klim.mean(), color=MERAH, ls="--", lw=1)
ax.annotate("rerata tahunan " + koma("%.2f" % klim.mean()), xy=(0.6, klim.mean()),
            xytext=(0, 3), textcoords="offset points", fontsize=6.8, color=MERAH)
ax.set_xticks(range(1, 13))
ax.set_xticklabels([n[:3] for n in NAMA_BULAN])
for b in bulan_idul:
    ax.get_xticklabels()[b - 1].set_fontweight("bold")
ax.set_xlim(0.4, 12.6)
ax.set_ylim(klim.min() - 0.12, klim.max() + 0.22)
rapikan(ax, "Rerata bulanan NO$_2$ troposferik Pulau Jawa, 2019–2025",
        None, "NO$_2$ ($\\times10^{-5}$ mol/m$^2$)")
ax.legend(frameon=False, loc="lower right", fontsize=7.5)
simpan(fig, "G4_01_rerata_bulanan.png")
print("bulanan: terendah %s %.2f | tertinggi %s %.2f | bulan Idul Fitri %.1f persen di bawah rerata"
      % (NAMA_BULAN[int(klim.argmin())], klim.min(), NAMA_BULAN[int(klim.argmax())], klim.max(),
         (klim[[b - 1 for b in bulan_idul]].mean() / klim.mean() - 1) * 100))


# ---------------------------------- Gambar 4.5 anomali se-Jawa tiap tahun
def batang_per_tahun(data, judul, nama_berkas, label_y="anomali NO$_2$ (%)"):
    fig, ax = plt.subplots(figsize=(LEBAR, 3.2))
    lebar = 0.27
    for i, (nama, nilai, warna) in enumerate(data):
        posisi = np.arange(len(TAHUN)) + (i - (len(data) - 1) / 2) * lebar
        ax.bar(posisi, nilai, width=lebar, label=nama, color=warna, edgecolor="white", lw=0.5)
        for x, v in zip(posisi, nilai):
            ax.annotate(koma("%+.1f" % v), (x, v), ha="center",
                        va="bottom" if v >= 0 else "top", fontsize=6.8, color=TINTA2,
                        xytext=(0, 2 if v >= 0 else -2), textcoords="offset points")
    ax.axhline(0, color=TINTA, lw=1)
    ax.set_xticks(range(len(TAHUN)))
    ax.set_xticklabels(TAHUN)
    rapikan(ax, judul, None, label_y)
    ax.legend(frameon=False, ncol=len(data), loc="upper center", bbox_to_anchor=(0.5, -0.1))
    return simpan(fig, nama_berkas)


batang_per_tahun(
    [("arus mudik (H−7…H0)", rerata_sejawa["mudik"].values, "#9CC3E3"),
     ("arus balik (H+1…H+7)", rerata_sejawa["balik"].values, "#4F8FC0"),
     ("gabungan (H−7…H+7)", rerata_sejawa["gab"].values, "#1F4E79")],
    "Anomali NO$_2$ se-Jawa setiap tahun menurut periode, rerata 117 wilayah",
    "G4_05_anomali_sejawa_per_tahun.png")

batang_per_tahun(
    [(nama, np.array(KAJIAN[nama]["gab"]["per_tahun"]), WARNA_KAJIAN[nama])
     for nama in WILAYAH_KAJIAN],
    "Anomali NO$_2$ periode gabungan setiap tahun pada keempat wilayah kajian",
    "L21_anomali_empat_wilayah_per_tahun.png")


# ------------------------------------ Gambar 4.7, 4.8, 4.9 deret harian
def deret(kolom, judul, label_y, nama_berkas, garis_nol=False, tinggi=3.1):
    fig, ax = plt.subplots(figsize=(LEBAR, tinggi))
    for nama in WILAYAH_KAJIAN:
        t = HARIAN[nama]
        ax.plot(t["hari"], t[kolom], marker="o", ms=4, lw=1.8,
                color=WARNA_KAJIAN[nama], label=nama)
    if garis_nol:
        ax.axhline(0, color=TINTA, lw=1)
    ax.axvline(0, color=TINTA2, ls=":", lw=1)
    ax.annotate("Idul Fitri", xy=(0, ax.get_ylim()[1]), xytext=(3, -12),
                textcoords="offset points", fontsize=8.5, color=TINTA2)
    ax.set_xticks(range(-7, 8))
    ax.set_xticklabels(["H%+d" % d if d else "H0" for d in range(-7, 8)], fontsize=7.5)
    rapikan(ax, judul, "hari terhadap Idul Fitri", label_y)
    ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    return simpan(fig, nama_berkas)


deret("anomali", "Anomali NO$_2$ harian pada keempat wilayah kajian, rerata 2019–2025",
      "anomali NO$_2$ (%)", "G4_07_anomali_harian.png", garis_nol=True)
deret("hujan", "Curah hujan harian pada keempat wilayah kajian, rerata 2019–2025",
      "curah hujan (mm/hari)", "G4_08_hujan_harian.png", tinggi=2.2)
deret("suhu", "Suhu udara harian pada keempat wilayah kajian, rerata 2019–2025",
      "suhu udara (°C)", "G4_09_suhu_harian.png", tinggi=2.2)


# ------------------------- Gambar 4.10 dan 4.11 diagram sebar per wilayah
def sebar_per_wilayah(kunci, label_x, judul, nama_berkas):
    fig, sumbu = plt.subplots(2, 2, figsize=(LEBAR, 4.1))
    for ax, nama, huruf in zip(sumbu.ravel(), WILAYAH_KAJIAN, "abcd"):
        titik = TITIK[nama][kunci]
        k = KOR[nama][kunci]
        nyata = k["p"] < 0.05
        ax.scatter(titik[:, 0], titik[:, 1], s=12, color=BIRU,
                   alpha=0.55, edgecolors="none", zorder=3)
        b, a = np.polyfit(titik[:, 0], titik[:, 1], 1)
        x = np.linspace(titik[:, 0].min(), titik[:, 0].max(), 2)
        ax.plot(x, a + b * x, color=TINTA, lw=2.2, zorder=4)
        ax.axhline(0, color=TINTA2, lw=0.9)
        ket = koma("r = %.3f · p = %.3f · n = %d" % (k["r"], k["p"], k["n"]))
        ax.text(0.03, 0.97, ket.replace("-", "−"),
                transform=ax.transAxes, va="top", fontsize=7.5, color=TINTA2,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=KISI, lw=1))
        rapikan(ax, nama, label_x, "anomali NO$_2$ (%)")
        ax.set_title("(%s)" % huruf, fontsize=9, loc="left")
    if JUDUL:
        fig.suptitle(judul, fontsize=11, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.97 if JUDUL else 1.0])
    return simpan(fig, nama_berkas)


sebar_per_wilayah("hujan", "curah hujan harian (mm)",
                  "Anomali NO$_2$ harian terhadap curah hujan harian di setiap wilayah kajian",
                  "G4_10_sebar_hujan_per_wilayah.png")
sebar_per_wilayah("suhu", "suhu udara harian (°C)",
                  "Anomali NO$_2$ harian terhadap suhu udara harian di setiap wilayah kajian",
                  "G4_11_sebar_suhu_per_wilayah.png")


def sebar_gabungan(kunci, label_x, judul, nama_berkas):
    fig, ax = plt.subplots(figsize=(LEBAR, 3.1))
    for nama in WILAYAH_KAJIAN:
        titik = TITIK[nama][kunci]
        k = KOR[nama][kunci]
        ax.scatter(titik[:, 0], titik[:, 1], s=12, alpha=0.5, edgecolors="none",
                   color=WARNA_KAJIAN[nama],
                   label="%s (r = %s; p = %s)" % (nama, koma("%.3f" % k["r"]), koma("%.3f" % k["p"])))
        b, a = np.polyfit(titik[:, 0], titik[:, 1], 1)
        x = np.linspace(titik[:, 0].min(), titik[:, 0].max(), 2)
        ax.plot(x, a + b * x, color=WARNA_KAJIAN[nama], lw=1.8)
    ax.axhline(0, color=TINTA2, lw=0.9)
    rapikan(ax, judul, label_x, "anomali NO$_2$ harian (%)")
    ax.legend(frameon=False, fontsize=7.5)
    return simpan(fig, nama_berkas)


sebar_gabungan("hujan", "curah hujan harian (mm)",
               "Anomali NO$_2$ harian terhadap curah hujan, gabungan keempat wilayah",
               "L22_sebar_hujan_gabungan.png")
sebar_gabungan("suhu", "suhu udara harian (°C)",
               "Anomali NO$_2$ harian terhadap suhu udara, gabungan keempat wilayah",
               "L23_sebar_suhu_gabungan.png")


# ------------------------- Gambar L.24 dan L.25 sebar antarwilayah se-Jawa
def sebar_antarwilayah(selisih, label_x, judul, nama_berkas, warna):
    k = korelasi(selisih[sejajar].values, anom_wilayah.values)
    nyata = k["p"] < 0.05
    fig, ax = plt.subplots(figsize=(LEBAR, 3.1))
    ax.scatter(selisih[sejajar].values, anom_wilayah.values, s=16, alpha=0.6,
               color=warna, edgecolors="none", zorder=3)
    b, a = np.polyfit(selisih[sejajar].values, anom_wilayah.values, 1)
    x = np.linspace(selisih.min(), selisih.max(), 2)
    ax.plot(x, a + b * x, color=MERAH if nyata else TINTA, lw=2.2, zorder=4)
    ax.axhline(0, color=TINTA2, lw=0.9)
    ket = koma("r = %.3f · p = %.3f · n = %d" % (k["r"], k["p"], k["n"]))
    ax.text(0.03, 0.05, ket + ("\nnyata, menerangkan " + koma("%.1f" % (k["r"] ** 2 * 100)) + "% keragaman"
                               if nyata else "\ntidak nyata"),
            transform=ax.transAxes, fontsize=9.5, color=MERAH if nyata else TINTA2,
            bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=MERAH if nyata else KISI, lw=1))
    rapikan(ax, judul, label_x, "anomali NO$_2$ (%)")
    return simpan(fig, nama_berkas)


sebar_antarwilayah(D_HUJAN, "selisih curah hujan Lebaran terhadap acuan (mm/hari)",
                   "Anomali NO$_2$ terhadap selisih curah hujan antarwilayah se-Jawa",
                   "L24_sebar_hujan_antarwilayah.png", BIRU)
sebar_antarwilayah(D_SUHU, "selisih suhu udara Lebaran terhadap acuan (°C)",
                   "Anomali NO$_2$ terhadap selisih suhu udara antarwilayah se-Jawa",
                   "L25_sebar_suhu_antarwilayah.png", JINGGA)


# --------------------- Gambar L.26 dan L.27 NO2 menurut kelas cuaca harian
KELAS_HUJAN = [("Tidak hujan", "< 0,5", 0, 0.5), ("Sangat ringan", "0,5–5", 0.5, 5),
               ("Ringan", "5–20", 5, 20), ("Sedang", "20–50", 20, 50),
               ("Lebat", "50–100", 50, 100), ("Sangat lebat", "> 100", 100, 1e9)]
KELAS_SUHU = [("Rendah", "< 25,0", -1e9, 25.0), ("Menengah", "25,0–27,0", 25.0, 27.0),
              ("Tinggi", "≥ 27,0", 27.0, 1e9)]


def gabung_harian(nama):
    """Satu tabel berisi NO2, hujan, dan suhu pada hari yang sama di satu wilayah."""
    a = H_NO2[H_NO2["wilayah"] == nama][["tanggal", "nilai"]].rename(columns={"nilai": "no2"})
    b = H_HUJ[H_HUJ["wilayah"] == nama][["tanggal", "nilai"]].rename(columns={"nilai": "hujan"})
    c = H_SUH[H_SUH["wilayah"] == nama][["tanggal", "nilai"]].rename(columns={"nilai": "suhu"})
    return a.merge(b, on="tanggal", how="inner").merge(c, on="tanggal", how="inner")


GABUNG = {nama: gabung_harian(nama) for nama in WILAYAH_KAJIAN}


def kotak_kelas(kelas, kolom, judul, label_x, nama_berkas):
    fig, sumbu = plt.subplots(2, 2, figsize=(LEBAR, 5.2))
    ringkasan = []
    for ax, nama in zip(sumbu.ravel(), WILAYAH_KAJIAN):
        t = GABUNG[nama]
        isi, label = [], []
        for judul_kelas, rentang, bawah, atas in kelas:
            pilih = t[(t[kolom] >= bawah) & (t[kolom] < atas)]["no2"].values
            if len(pilih) == 0:
                continue
            isi.append(pilih)
            label.append("%s\n%s\n(n = %d)" % (judul_kelas.replace(" ", "\n"), rentang, len(pilih)))
        kotak = ax.boxplot(isi, patch_artist=True, widths=0.6,
                           medianprops=dict(color=MERAH, lw=1.6),
                           flierprops=dict(marker="o", ms=3, mfc=TINTA2, mec="none", alpha=0.4))
        for badan in kotak["boxes"]:
            badan.set(facecolor="#D6E4F0", edgecolor=TINTA2, lw=0.9)
        ax.set_xticklabels(label, fontsize=6.5)
        rapikan(ax, nama, None, "NO$_2$ ($\\times10^{-5}$ mol/m$^2$)")
        ax.set_ylim(top=ax.get_ylim()[1] * 1.25)
        ax.set_title(nama, fontsize=9, fontweight="bold")
        if len(isi) > 1:
            H, p = stats.kruskal(*isi)
            ringkasan.append({"wilayah": nama, "kolom": kolom, "H": H, "df": len(isi) - 1, "p": p})
            ax.text(0.98, 0.97, "Kruskal-Wallis\nH = %s; p %s" % (koma("%.2f" % H), "< 0,0001" if p < 1e-4 else "= " + koma("%.4f" % p)),
                    transform=ax.transAxes, ha="right", va="top", fontsize=7,
                    color=MERAH if p < 0.05 else TINTA2)
    if JUDUL:
        fig.suptitle(judul, fontsize=11, fontweight="bold")
    fig.supxlabel(label_x, fontsize=9.5)
    fig.tight_layout(rect=[0, 0.02, 1, 0.97 if JUDUL else 1.0])
    simpan(fig, nama_berkas)
    return pd.DataFrame(ringkasan)


UJI_KELAS_HUJAN = kotak_kelas(KELAS_HUJAN, "hujan",
                              "Sebaran NO$_2$ menurut kelas intensitas curah hujan BMKG",
                              "kelas curah hujan harian (mm)", "L26_no2_kelas_hujan.png")
UJI_KELAS_SUHU = kotak_kelas(KELAS_SUHU, "suhu",
                             "Sebaran NO$_2$ menurut kelas suhu udara",
                             "kelas suhu udara harian (°C)", "L27_no2_kelas_suhu.png")

# ------------------------------------- Gambar L.28 sebaran suhu harian
fig, ax = plt.subplots(figsize=(LEBAR, 2.9))
isi = [GABUNG[nama]["suhu"].values for nama in WILAYAH_KAJIAN]
kotak = ax.boxplot(isi, patch_artist=True, widths=0.55,
                   medianprops=dict(color=MERAH, lw=1.6),
                   flierprops=dict(marker="o", ms=3, mfc=TINTA2, mec="none", alpha=0.4))
for badan, nama in zip(kotak["boxes"], WILAYAH_KAJIAN):
    badan.set(facecolor=WARNA_KAJIAN[nama], alpha=0.35, edgecolor=TINTA2, lw=0.9)
ax.set_xticklabels(["%s\n(n = %d)" % (n, len(GABUNG[n])) for n in WILAYAH_KAJIAN], fontsize=9)
for batas in (25.0, 27.0):
    ax.axhline(batas, color=TINTA2, ls="--", lw=1,
               label="batas kelas suhu (25,0 dan 27,0 °C)" if batas == 25.0 else None)
ax.legend(frameon=False, loc="upper right")
rapikan(ax, "Sebaran suhu udara harian keempat wilayah kajian", None, "suhu udara (°C)")
simpan(fig, "L28_sebaran_suhu_harian.png")

# --------------------------- Gambar L.29 kolom NO2 terhadap indeks ISPU
fig, ax = plt.subplots(figsize=(LEBAR, 3.3))
ax.scatter(PASANG["no2"], PASANG["satelit"], s=18, color=HIJAU, alpha=0.65,
           edgecolors="none", zorder=3)
b, a = np.polyfit(PASANG["no2"], PASANG["satelit"], 1)
x = np.linspace(PASANG["no2"].min(), PASANG["no2"].max(), 2)
ax.plot(x, a + b * x, color=TINTA, lw=2.2, zorder=4)
ax.text(0.03, 0.97, koma("Spearman ρ = %.3f · Pearson r = %.3f · n = %d" % (rs, rp, len(PASANG))) + "\np < 0,001", transform=ax.transAxes, va="top", fontsize=8,
        bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=MERAH, lw=1), color=MERAH)
rapikan(ax, "Kolom NO$_2$ Sentinel-5P DKI Jakarta terhadap indeks NO$_2$ ISPU, 2022",
        "indeks NO$_2$ ISPU DKI Jakarta", "NO$_2$ Sentinel-5P ($\\times10^{-5}$ mol/m$^2$)")
simpan(fig, "L29_ispu_terhadap_satelit.png")


# ============================================ peta lampiran tiap tahun ==
PERIODE_PETA = [("acD", "periode acuan"), ("gab", "jendela Lebaran"),
                ("mudik", "arus mudik"), ("balik", "arus balik")]
BESARAN = [
    ("NO2", NO2, E5, "NO$_2$ troposferik ($\\times10^{-5}$ mol/m$^2$)", "YlOrRd"),
    ("HUJAN", HUJ, 1.0, "curah hujan (mm/hari)", "YlGnBu"),
    ("SUHU", SUH, 1.0, "suhu udara (°C)", "YlOrBr"),
]
nomor_lampiran = 1
for kode, tabel, faktor, satuan, palet in BESARAN:
    for periode, nama_periode in PERIODE_PETA:
        daftar = []
        for t in TAHUN:
            s = pd.Series((tabel[f"{periode}_{t}"] * faktor).values, index=tabel["wilayah"].values)
            if kode == "SUHU" and s.mean() > 200:
                s = s - 273.15
            daftar.append((str(t), s))
        rerata = pd.concat([s for _, s in daftar], axis=1).mean(axis=1)
        daftar.append(("rerata 2019–2025", rerata))
        peta_banyak(daftar,
                    "%s pada %s tiap tahun" % (satuan.split(" (")[0], nama_periode),
                    satuan, "L%02d_peta_%s_%s.png" % (nomor_lampiran, kode.lower(), periode),
                    palet=palet, kolom=4)
        nomor_lampiran += 1

# -------------------------------- peta NO2 dua belas bulan tiap tahun
semua_bulanan = (BULANAN[kolom_bulan] * E5).values
vmin_b, vmaks_b = np.nanpercentile(semua_bulanan, 2), np.nanpercentile(semua_bulanan, 98)
for t in TAHUN:
    daftar = []
    for b in range(1, 13):
        kolom = f"b{t}_{b:02d}"
        s = pd.Series((BULANAN[kolom] * E5).values, index=BULANAN["ADM2_NAME"].str.strip().values)
        daftar.append((NAMA_BULAN[b - 1], s))
    peta_banyak(daftar, "NO$_2$ troposferik Pulau Jawa dua belas bulan tahun %d" % t,
                "NO$_2$ troposferik ($\\times10^{-5}$ mol/m$^2$)",
                "L%02d_peta_bulanan_%d.png" % (12 + (t - 2018), t),
                palet="YlOrRd", vmin=vmin_b, vmax=vmaks_b, kolom=4)


# =================================================== tabel untuk naskah ==
def tulis(tabel, nama):
    jalur = os.path.join(OLAHAN, nama)
    tabel.to_csv(jalur, index=False, encoding="utf-8-sig")
    print("  tabel :", nama)


# Tabel 4.1 perubahan NO2 keempat wilayah kajian
baris = []
for nama in WILAYAH_KAJIAN:
    d = KAJIAN[nama]
    baris.append({
        "wilayah": nama,
        "peran": "asal" if nama in ["DKI Jakarta", "Kota Surabaya"] else "tujuan",
        "NO2_hari_biasa_1e-5_mol_m2": round(d["aras"], 2),
        "arus_mudik_persen": round(d["mudik"]["rerata"], 1),
        "arus_balik_persen": round(d["balik"]["rerata"], 1),
        "gabungan_persen": round(d["gab"]["rerata"], 1),
        "tahun_turun": "%d dari 7" % d["gab"]["turun"],
        "p_wilcoxon_gabungan": round(d["gab"]["p"], 4),
    })
tulis(pd.DataFrame(baris), "T4_1_perubahan_empat_wilayah.csv")

# Tabel 4.2 ringkasan sepuluh uji keterkaitan dengan cuaca
baris = [{"skala": "antarwilayah se-Jawa", "wilayah": "117 kabupaten dan kota",
          "peubah": peubah, "r": round(KOR_JAWA[k]["r"], 3), "p": round(KOR_JAWA[k]["p"], 3),
          "n": KOR_JAWA[k]["n"], "nyata": "ya" if KOR_JAWA[k]["p"] < 0.05 else "tidak"}
         for k, peubah in [("hujan", "curah hujan"), ("suhu", "suhu udara")]]
for nama in WILAYAH_KAJIAN:
    for k, peubah in [("hujan", "curah hujan"), ("suhu", "suhu udara")]:
        d = KOR[nama][k]
        baris.append({"skala": "antarhari", "wilayah": nama, "peubah": peubah,
                      "r": round(d["r"], 3), "p": round(d["p"], 3), "n": d["n"],
                      "nyata": "ya" if d["p"] < 0.05 else "tidak"})
TABEL_UJI = pd.DataFrame(baris)
tulis(TABEL_UJI, "T4_2_ringkasan_uji_cuaca.csv")
print("uji nyata: %d dari %d" % ((TABEL_UJI["nyata"] == "ya").sum(), len(TABEL_UJI)))

# Tabel L.1 perubahan se-Jawa menurut periode
tulis(pd.DataFrame([{"periode": nama, "rerata_persen": round(SEJAWA[k]["rerata"], 2),
                     "tahun_turun": "%d dari 7" % SEJAWA[k]["turun"],
                     "p_wilcoxon": round(SEJAWA[k]["p"], 4)}
                    for k, nama in [("mudik", "arus mudik H−7 sampai H0"),
                                    ("balik", "arus balik H+1 sampai H+7"),
                                    ("gab", "gabungan H−7 sampai H+7")]]),
      "TL_1_perubahan_sejawa_periode.csv")

# Tabel L.2 anomali gabungan se-Jawa tiap tahun
tulis(pd.DataFrame({"tahun": TAHUN, "idul_fitri": [IDUL[t] for t in TAHUN],
                    "anomali_gabungan_persen": np.round(rerata_sejawa["gab"].values, 2),
                    "anomali_mudik_persen": np.round(rerata_sejawa["mudik"].values, 2),
                    "anomali_balik_persen": np.round(rerata_sejawa["balik"].values, 2)}),
      "TL_2_anomali_sejawa_tiap_tahun.csv")

# Tabel L.3 perbandingan tiga calon periode acuan
baris = []
for kode, keterangan in [("acA", "acuan A, dua bulan Hijriah sebelum Ramadan"),
                         ("acD", "acuan D, H−60..H−31 dan H+30..H+59 (dipakai)"),
                         ("acE", "acuan E, H+30..H+59 saja")]:
    if kode == "acA":
        acu = {t: NO2["acA"] for t in TAHUN}
    else:
        acu = {t: NO2[f"{kode}_{t}"] for t in TAHUN}
    a = pd.DataFrame({t: (NO2[f"gab_{t}"] - acu[t]) / acu[t] * 100 for t in TAHUN})
    per_tahun = a.mean(axis=0)
    baris.append({"acuan": keterangan, "anomali_gabungan_persen": round(per_tahun.mean(), 2),
                  "tahun_turun": "%d dari 7" % int((per_tahun < 0).sum()),
                  "p_wilcoxon": round(wilcoxon_p(per_tahun.tolist()), 4),
                  "wilayah_naik": int((a.mean(axis=1) > 0).sum())})
tulis(pd.DataFrame(baris), "TL_3_perbandingan_tiga_acuan.csv")

# Tabel L.4 perubahan menurut kelompok wilayah
baris = []
for nama_kel, anggota in [("%d kota asal" % len(KEL_ASAL), KEL_ASAL),
                          ("%d kabupaten tujuan" % len(KEL_TUJUAN), KEL_TUJUAN)]:
    isi = {"kelompok": nama_kel, "jumlah_wilayah": len(anggota),
           "NO2_hari_biasa_1e-5_mol_m2": round(ARAS[anggota].mean(), 2)}
    for p, label in [("mudik", "arus_mudik"), ("balik", "arus_balik"), ("gab", "gabungan")]:
        isi[label + "_persen"] = round(ANOM[p].loc[anggota].mean(axis=1).mean(), 2)
    baris.append(isi)
tulis(pd.DataFrame(baris), "TL_4_perubahan_kelompok_wilayah.csv")
tulis(pd.DataFrame({"kelompok": ["kota asal"] * len(KEL_ASAL) + ["kabupaten tujuan"] * len(KEL_TUJUAN),
                    "wilayah": KEL_ASAL + KEL_TUJUAN,
                    "NO2_hari_biasa": np.round(ARAS[KEL_ASAL + KEL_TUJUAN].values, 2),
                    "anomali_gabungan_persen": np.round(anom_wilayah[KEL_ASAL + KEL_TUJUAN].values, 2)}),
      "TL_4b_anggota_kelompok.csv")

# Tabel L.5 peringkat anomali se-Jawa
urut = anom_wilayah.sort_values()
prov = pd.Series(NO2["provinsi"].values, index=NO2["wilayah"].values)
peringkat = pd.DataFrame({
    "peringkat": list(range(1, 13)) + list(range(1, 13)),
    "kelompok": ["turun terbesar"] * 12 + ["naik tertinggi"] * 12,
    "wilayah": list(urut.index[:12]) + list(urut.index[-12:][::-1]),
    "provinsi": list(prov[urut.index[:12]]) + list(prov[urut.index[-12:][::-1]]),
    "anomali_persen": np.round(list(urut.values[:12]) + list(urut.values[-12:][::-1]), 1),
})
tulis(peringkat, "TL_5_peringkat_anomali.csv")

# Tabel L.6 luas dan perkiraan cacah petak wilayah kajian
KM2 = 111.32 * 111.32 * np.cos(np.deg2rad(6.5))     # derajat persegi ke km2 di lintang Jawa
baris = []
for nama in WILAYAH_KAJIAN:
    if nama == "DKI Jakarta":
        luas = NO2.loc[NO2["provinsi"].str.lower() == "dki jakarta", "Shape_Area"].sum() * KM2
    else:
        luas = NO2.loc[NO2["wilayah"] == nama, "Shape_Area"].sum() * KM2
    baris.append({"wilayah": nama, "luas_km2": round(luas),
                  "petak_sentinel5p_3,5x5,5km": round(luas / (3.5 * 5.5)),
                  "petak_chirps_5,5km": round(luas / (5.55 * 5.52)),
                  "petak_era5land_11km": round(luas / (11.1 * 11.03), 1)})
tulis(pd.DataFrame(baris), "TL_6_luas_dan_cacah_petak.csv")

# tabel pendukung: anomali tiap wilayah tiap tahun, dan deret harian
anom_lengkap = ANOM["gab"].copy()
anom_lengkap.insert(0, "provinsi", prov[anom_lengkap.index].values)
anom_lengkap["rerata"] = anom_wilayah.values
anom_lengkap.index.name = "wilayah"
tulis(anom_lengkap.round(2).reset_index(), "anomali_gabungan_117_wilayah.csv")
tulis(pd.concat([HARIAN[n].assign(wilayah=n) for n in WILAYAH_KAJIAN]).round(3),
      "deret_harian_empat_wilayah.csv")
tulis(pd.DataFrame({"bulan": NAMA_BULAN, "rerata_no2_1e-5_mol_m2": np.round(klim, 3)}),
      "rerata_bulanan_sejawa.csv")

RINGKASAN = {
    "disusun_dengan": "analisis_no2_lebaran.py",
    "jumlah_wilayah": int(len(NO2)),
    "sejawa": {k: SEJAWA[k] for k in SEJAWA},
    "wilayah_kajian": KAJIAN,
    "korelasi_antarhari": KOR,
    "korelasi_antarwilayah": KOR_JAWA,
    "rerata_selisih_cuaca": {"hujan_mm_per_hari": float(D_HUJAN.mean()),
                             "suhu_derajat": float(D_SUHU.mean())},
    "ispu": ISPU_HASIL,
    "kelompok": {"kota_asal": KEL_ASAL, "kabupaten_tujuan": KEL_TUJUAN,
                 "kuartil_bawah": float(Q1), "kuartil_atas": float(Q3)},
    "bulanan": {NAMA_BULAN[i]: float(klim[i]) for i in range(12)},
}
with open(os.path.join(OLAHAN, "ringkasan_angka.json"), "w", encoding="utf8") as f:
    json.dump(RINGKASAN, f, indent=1, ensure_ascii=False)
print("\nselesai. gambar ada di folder Gambar, tabel di Data/02_olahan")
