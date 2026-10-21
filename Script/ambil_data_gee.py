"""
Pengambilan data dari Google Earth Engine memakai antarmuka Python.

Skrip ini yang menghasilkan seluruh berkas di Data/01_mentah. Keluarannya
dikirim ke Google Drive sebagai CSV, lalu diunduh ke folder tersebut.
Jalankan di Google Colab supaya autentikasinya mudah:

    import ee
    ee.Authenticate()
    ee.Initialize(project='nama-proyek-anda')

Catatan satuan:
    NO2   kolom troposferik, mol/m2. Pada pengolahan dikalikan 1e5.
    Hujan CHIRPS, mm. Setiap jendela dibagi jumlah harinya sehingga
          satuannya menjadi mm per hari dan dapat dibandingkan antarjendela.
    Suhu  ERA5-Land, kelvin. Dikurangi 273,15 pada saat pengolahan.

Arya Perdana Putra Nasution / 12822007 / Meteorologi ITB
"""

import ee

# ee.Authenticate()
# ee.Initialize(project="ganti-dengan-proyek-anda")

FOLDER_DRIVE = "Skripsi_NO2_Lebaran"
BAND = "tropospheric_NO2_column_number_density"
TAHUN = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
IDUL = {2019: "2019-06-05", 2020: "2020-05-24", 2021: "2021-05-13",
        2022: "2022-05-02", 2023: "2023-04-22", 2024: "2024-04-10",
        2025: "2025-03-31"}
BULAN_IDUL = {2019: 6, 2020: 5, 2021: 5, 2022: 5, 2023: 4, 2024: 4, 2025: 3}
PROVINSI = ["Dki Jakarta", "Jawa Barat", "Jawa Tengah", "Jawa Timur",
            "Daerah Istimewa Yogyakarta", "Banten"]
WILAYAH_KAJIAN = ["Kota Surabaya", "Purbalingga", "Ponorogo"]

# 117 kabupaten dan kota di Pulau Jawa
KAB = (ee.FeatureCollection("FAO/GAUL/2015/level2")
       .filter(ee.Filter.eq("ADM0_NAME", "Indonesia"))
       .filter(ee.Filter.inList("ADM1_NAME", PROVINSI)))

# jendela Lebaran tujuh tahun, dipakai untuk membuang hari Lebaran dari acuan E
SARINGAN_LEBARAN = ee.Filter.Or(*[
    ee.Filter.date(ee.Date(IDUL[t]).advance(-7, "day"), ee.Date(IDUL[t]).advance(8, "day"))
    for t in TAHUN])


def koleksi_no2_harian():
    """Satu citra per hari: rerata seluruh orbit hari itu, petak negatif dibuang.

    Kolom NO2 hasil pengambilan kadang bernilai negatif karena galat
    pengambilan pada kadar rendah. Petak seperti itu dibuang, bukan
    dijadikan nol, supaya tidak menarik rerata ke bawah.
    """
    s5p = ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_NO2").select(BAND)
    mulai, jumlah_hari = ee.Date("2018-07-01"), 2740

    def satu_hari(i):
        d0 = mulai.advance(ee.Number(i), "day")
        sehari = s5p.filterDate(d0, d0.advance(1, "day"))
        citra = ee.Image(ee.Algorithms.If(
            sehari.size().gt(0), sehari.mean().toFloat(),
            ee.Image(0).selfMask().toFloat().rename(BAND)))
        return citra.updateMask(citra.gte(0)).set("system:time_start", d0.millis())

    return ee.ImageCollection(ee.List.sequence(0, jumlah_hari - 1).map(satu_hari))


def susun_pita(harian, cara):
    """Semua pita periode untuk satu koleksi harian.

    cara = 'jumlah' untuk curah hujan (dijumlahkan lalu dibagi jumlah hari),
    cara = 'rata' untuk NO2 dan suhu.

    Pita yang dihasilkan:
        acA          acuan A, H-325..H-31 dirata-rata untuk tujuh tahun
        acD_<tahun>  acuan D, rerata H-60..H-31 dan H+30..H+59 (dipakai di naskah)
        acE_<tahun>  acuan E, bulan Masehi tempat Idul Fitri jatuh, tanpa jendela Lebaran
        mudik_<tahun>, balik_<tahun>, gab_<tahun>
    """
    def gabung(koleksi):
        return ee.Image(koleksi.sum() if cara == "jumlah" else koleksi.mean()).toFloat()

    def jendela(tahun, a, b):
        h0 = ee.Date(IDUL[tahun])
        return gabung(harian.filterDate(h0.advance(a, "day"), h0.advance(b + 1, "day")))

    def per_hari(citra, n):
        return citra.divide(n) if cara == "jumlah" else citra

    acuan_a = ee.ImageCollection([per_hari(jendela(t, -325, -31), 295)
                                  for t in TAHUN]).mean().toFloat()
    pita = [acuan_a.rename("acA")]
    for t in TAHUN:
        pita.append(per_hari(jendela(t, -7, 0), 8).rename(f"mudik_{t}"))
        pita.append(per_hari(jendela(t, 1, 7), 7).rename(f"balik_{t}"))
        pita.append(per_hari(jendela(t, -7, 7), 15).rename(f"gab_{t}"))
        pita.append(ee.ImageCollection([per_hari(jendela(t, -60, -31), 30),
                                        per_hari(jendela(t, 30, 59), 30)])
                    .mean().toFloat().rename(f"acD_{t}"))
        bulan = (harian.filter(ee.Filter.calendarRange(BULAN_IDUL[t], BULAN_IDUL[t], "month"))
                 .filter(SARINGAN_LEBARAN.Not()))
        acuan_e = ee.Image(bulan.sum().divide(bulan.size()) if cara == "jumlah"
                           else bulan.mean()).toFloat()
        pita.append(acuan_e.rename(f"acE_{t}"))
    return ee.Image.cat(pita)


def kirim(tabel, nama):
    tugas = ee.batch.Export.table.toDrive(collection=tabel, description=nama,
                                          folder=FOLDER_DRIVE, fileFormat="CSV")
    tugas.start()
    print("tugas dikirim:", nama)


# ------------------------------------------------ nilai periode per wilayah
def ekspor_periode():
    """v11_*: nilai tiap periode tiap tahun untuk 117 kabupaten dan kota.

    Skala 500 m dipakai untuk NO2 karena delapan kota kecil (antara lain Kota
    Cimahi dan Kota Magelang) lebih sempit daripada satu petak 1113 m, sehingga
    pada skala asli tidak ada pusat petak yang jatuh di dalamnya dan hasilnya
    kosong. Nilainya tetap berasal dari petak 1113 m yang sama, hanya
    pencuplikannya yang dirapatkan.
    """
    no2 = susun_pita(koleksi_no2_harian(), "rata")
    kirim(no2.reduceRegions(collection=KAB, reducer=ee.Reducer.mean(), scale=500,
                            tileScale=16), "v11_NO2_perKabupaten_500m")

    hujan = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").select("precipitation") \
        .filterDate("2018-07-01", "2026-01-01")
    kirim(susun_pita(hujan, "jumlah").reduceRegions(collection=KAB, reducer=ee.Reducer.mean(),
                                                    scale=1000, tileScale=16),
          "v11_Hujan_perKabupaten_CHIRPS")

    suhu = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR").select("temperature_2m") \
        .filterDate("2018-07-01", "2026-01-01")
    kirim(susun_pita(suhu, "rata").reduceRegions(collection=KAB, reducer=ee.Reducer.mean(),
                                                 scale=1000, tileScale=16),
          "v11_Suhu_perKabupaten_ERA5Land")


# ------------------------------------------------------- NO2 tiap bulan
def ekspor_bulanan():
    """v16: rerata NO2 tiap bulan 2019-2025 untuk tiap kabupaten dan kota.

    Seluruh bulan disusun sebagai pita pada satu citra lalu direduksi sekali,
    karena memanggil reduceRegions 84 kali membuat tugasnya kehabisan waktu.
    """
    harian = koleksi_no2_harian()
    pita = []
    for t in TAHUN:
        for b in range(1, 13):
            mulai = ee.Date.fromYMD(t, b, 1)
            sebulan = harian.filterDate(mulai, mulai.advance(1, "month"))
            pita.append(sebulan.mean().toFloat().rename(f"b{t}_{b:02d}"))
    kirim(ee.Image.cat(pita).reduceRegions(collection=KAB, reducer=ee.Reducer.mean(),
                                           scale=500, tileScale=4),
          "v16_NO2_Bulanan_perKabupaten")


# --------------------------------------------------- deret harian wilayah
def ekspor_harian():
    """v13: NO2, curah hujan, dan suhu harian untuk wilayah kajian.

    Rentang harinya dibatasi pada H-60 sampai H+59 tiap tahun supaya berkasnya
    ramping; jendela itu sudah memuat periode Lebaran beserta acuannya.
    """
    wilayah = KAB.filter(ee.Filter.inList("ADM2_NAME", WILAYAH_KAJIAN))
    sumber = {
        "NO2": (koleksi_no2_harian(), 500),
        "Hujan": (ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").select("precipitation"), 1000),
        "Suhu": (ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR").select("temperature_2m"), 1000),
    }
    for nama, (koleksi, skala) in sumber.items():
        baris = []
        for t in TAHUN:
            h0 = ee.Date(IDUL[t])
            potong = koleksi.filterDate(h0.advance(-60, "day"), h0.advance(60, "day"))

            def satu_citra(citra):
                tanggal = ee.Date(citra.get("system:time_start")).format("YYYY-MM-dd")
                return citra.reduceRegions(collection=wilayah, reducer=ee.Reducer.mean(),
                                           scale=skala, tileScale=8) \
                    .map(lambda f: f.set("tanggal", tanggal))

            baris.append(potong.map(satu_citra).flatten())
        gabung = ee.FeatureCollection(baris).flatten() \
            .select(["tanggal", "ADM2_NAME", "mean"], ["tanggal", "wilayah", "nilai"])
        kirim(gabung, f"v13_Harian_{nama}")


# ------------------------------------------ DKI Jakarta sebagai satu wilayah
def ekspor_dki():
    """v18: DKI Jakarta digabung menjadi satu wilayah.

    Pada naskah DKI Jakarta dipakai utuh satu provinsi, bukan salah satu kota
    administrasinya, sehingga poligon kelima kota disatukan lebih dulu.
    """
    dki = KAB.filter(ee.Filter.eq("ADM1_NAME", "Dki Jakarta"))
    satu = ee.Feature(dki.geometry().dissolve(), {"wilayah": "DKI Jakarta"})
    jakarta_timur = ee.Feature(
        dki.filter(ee.Filter.eq("ADM2_NAME", "Kota Jakarta Timur")).geometry(),
        {"wilayah": "Kota Jakarta Timur"})          # pembanding dengan berkas v11
    wilayah = ee.FeatureCollection([satu, jakarta_timur])

    kirim(susun_pita(koleksi_no2_harian(), "rata")
          .reduceRegions(collection=wilayah, reducer=ee.Reducer.mean(),
                         scale=500, tileScale=16), "v18_NO2_Periode_DKI")

    no2, hujan, suhu = (koleksi_no2_harian(),
                        ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").select("precipitation"),
                        ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR").select("temperature_2m"))
    baris = []
    for t in TAHUN:
        h0 = ee.Date(IDUL[t])
        hari = ee.List.sequence(-60, 59)

        def satu_hari(n):
            d0 = h0.advance(ee.Number(n), "day")
            d1 = d0.advance(1, "day")
            citra = ee.Image.cat([
                no2.filterDate(d0, d1).mean().toFloat().rename("no2"),
                hujan.filterDate(d0, d1).sum().toFloat().rename("hujan"),
                suhu.filterDate(d0, d1).mean().toFloat().rename("suhu"),
            ])
            return citra.reduceRegions(collection=wilayah, reducer=ee.Reducer.mean(),
                                       scale=500, tileScale=8) \
                .map(lambda f: f.set("tanggal", d0.format("YYYY-MM-dd")))

        baris.append(ee.FeatureCollection(hari.map(satu_hari)).flatten())
    kirim(ee.FeatureCollection(baris).flatten()
          .select(["tanggal", "wilayah", "no2", "hujan", "suhu"]), "v18_Harian_DKI")


# ----------------------------------------------------- batas administratif
def ekspor_batas():
    """v5: batas provinsi untuk garis pantai dan garis batas pada peta."""
    provinsi = KAB.reduceColumns(ee.Reducer.toList(), ["ADM1_NAME"])
    del provinsi
    gabung = ee.FeatureCollection([
        ee.Feature(KAB.filter(ee.Filter.eq("ADM1_NAME", p)).geometry().dissolve(), {"nama": p})
        for p in PROVINSI])
    tugas = ee.batch.Export.table.toDrive(collection=gabung, description="v5_Batas_Provinsi_Jawa",
                                          folder=FOLDER_DRIVE, fileFormat="GeoJSON")
    tugas.start()
    print("tugas dikirim: v5_Batas_Provinsi_Jawa")


# ------------------------------------------- peta NO2 pada grid aslinya
def ekspor_raster():
    """v15: NO2 per petak 0,01° untuk tiap tahun, sebelum dirata-ratakan per wilayah.

    Empat pita berurutan untuk setiap tahun, yaitu acuan D, gabungan, arus mudik,
    dan arus balik, sehingga seluruhnya 28 pita untuk tujuh tahun. Dipakai pada
    Gambar 4.2, 4.3, dan panel (a) Gambar 4.4.
    """
    harian = koleksi_no2_harian()

    def jendela(tahun, a, b):
        h0 = ee.Date(IDUL[tahun])
        return harian.filterDate(h0.advance(a, "day"), h0.advance(b + 1, "day")).mean().toFloat()

    pita = []
    for t in TAHUN:
        acuan_d = ee.ImageCollection([jendela(t, -60, -31), jendela(t, 30, 59)]).mean().toFloat()
        pita.append(acuan_d.rename(f"acD_{t}"))
        pita.append(jendela(t, -7, 7).rename(f"gab_{t}"))
        pita.append(jendela(t, -7, 0).rename(f"mudik_{t}"))
        pita.append(jendela(t, 1, 7).rename(f"balik_{t}"))
    citra = ee.Image.cat(pita).clip(KAB.geometry())
    tugas = ee.batch.Export.image.toDrive(
        image=citra, description="v15_Raster_perTahun", folder=FOLDER_DRIVE,
        scale=1113, crs="EPSG:4326", region=KAB.geometry().bounds(),
        maxPixels=1e10, fileFormat="GeoTIFF")
    tugas.start()
    print("tugas dikirim: v15_Raster_perTahun")


if __name__ == "__main__":
    ekspor_periode()
    ekspor_bulanan()
    ekspor_harian()
    ekspor_dki()
    ekspor_batas()
    ekspor_raster()
    print("Semua tugas dikirim. Pantau di https://code.earthengine.google.com/tasks")
