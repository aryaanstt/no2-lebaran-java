# Data dan skrip tugas akhir

**Analisis spasio-temporal konsentrasi nitrogen dioksida (NO₂) di Pulau Jawa dan
beberapa kota selama periode Lebaran tahun 2019–2025 berbasis data Sentinel-5P
serta kaitannya dengan curah hujan dan suhu udara**

Arya Perdana Putra Nasution — 12822007 — Program Studi Meteorologi, FITB ITB

Folder ini memuat seluruh data dan skrip yang dipakai pada naskah. Dijalankan dari
awal sampai akhir, isinya menghasilkan kembali setiap angka dan setiap gambar yang
ada di Bab 4 dan Lampiran.

## Isi folder

```
ARSIP_TA_12822007/
├── BACA_DULU.md                     berkas ini
├── Data/
│   ├── KAMUS_DATA.md                keterangan tiap berkas: sumber, kolom, satuan
│   ├── 01_mentah/                   sepuluh berkas ekspor Earth Engine + ISPU DKI
│   └── 02_olahan/                   tabel hasil hitungan, dibuat ulang oleh notebook
├── Gambar/                          40 gambar keluaran notebook
└── Script/
    ├── ambil_data_gee.py            pengambilan data dari Google Earth Engine
    ├── analisis_no2_lebaran.ipynb   notebook Colab: pengolahan dan seluruh gambar
    └── analisis_no2_lebaran.py      isi notebook yang sama dalam bentuk skrip biasa
```

## Cara menjalankan

Ada dua tahap, dan tahap pertama tidak perlu diulang karena hasilnya sudah ada di
`Data/01_mentah`.

**Tahap 1, pengambilan data.** `Script/ambil_data_gee.py` mengirim tugas ekspor ke
Google Earth Engine. Jalankan di Colab, autentikasi Earth Engine dulu, lalu unduh
hasilnya dari Google Drive ke `Data/01_mentah`. Tahap ini memakan waktu berjam-jam
pada sisi Earth Engine.

**Tahap 2, pengolahan dan penggambaran.** Buka
`Script/analisis_no2_lebaran.ipynb` di Google Colab, unggah folder ini ke Google
Drive, lalu jalankan semua sel dari atas ke bawah. Notebook hanya memerlukan
pustaka yang sudah tersedia di Colab, yaitu numpy, pandas, matplotlib, scipy, dan
tifffile untuk membaca berkas raster `v15_Raster_perTahun.tif`.
Poligon wilayah ikut terbawa pada berkas CSV sehingga peta dapat digambar tanpa
pustaka peta tambahan.

Kalau ingin dijalankan di komputer sendiri, `python Script/analisis_no2_lebaran.py`
memberi hasil yang sama persis.

## Angka utama sebagai pemeriksa

Kalau notebook berjalan benar, keluarannya memuat angka berikut, sama seperti di
naskah.

| Angka | Nilai |
|---|---|
| Anomali NO₂ se-Jawa, periode gabungan | −7,84% |
| Sel grid daratan yang menurun, resolusi 0,01° | 68,5% |
| Wilayah yang justru naik | 18 dari 117 |
| Tahun yang menurun se-Jawa | 7 dari 7, p Wilcoxon 0,0156 |
| Se-Jawa tanpa tahun 2020 | −6,06%, 6 dari 6 tahun, p 0,0313 |
| DKI Jakarta | −20,5%, 6 dari 7 tahun, p 0,0313 |
| Kota Surabaya | −20,7%, 6 dari 7 tahun, p 0,0313 |
| Purbalingga dan Ponorogo | +5,0% dan +2,0%, tidak nyata |
| Korelasi antarwilayah, hujan dan suhu | r −0,152 (p 0,102) dan r −0,217 (p 0,019) |
| Uji korelasi yang nyata | 2 dari 10 |
| Sentinel-5P terhadap ISPU DKI 2022 | Spearman 0,471, n 84 |

## Gambar mana untuk gambar naskah yang mana

| Berkas di `Gambar/` | Gambar pada naskah |
|---|---|
| `G4_01_rerata_bulanan.png` | Gambar 4.1 |
| `G4_02_no2_lebaran.png` | Gambar 4.2 |
| `G4_03_no2_acuan.png` | Gambar 4.3 |
| `G4_04_anomali.png` | Gambar 4.4 |
| `G4_05_anomali_sejawa_per_tahun.png` | Gambar 4.5 |
| `G4_06_wilayah_kajian.png` | Gambar 4.6 |
| `G4_07_anomali_harian.png` | Gambar 4.7 |
| `G4_08_hujan_harian.png` | Gambar 4.8 |
| `G4_09_suhu_harian.png` | Gambar 4.9 |
| `G4_10_sebar_hujan_per_wilayah.png` | Gambar 4.10 |
| `G4_11_sebar_suhu_per_wilayah.png` | Gambar 4.11 |
| `L01`–`L04_peta_no2_*.png` | Gambar L.1 sampai L.4 |
| `L05`–`L08_peta_hujan_*.png` | tidak dipakai pada naskah revisi, disimpan sebagai arsip |
| `L09`–`L12_peta_suhu_*.png` | tidak dipakai pada naskah revisi, disimpan sebagai arsip |
| `L13`–`L19_peta_bulanan_<tahun>.png` | Gambar L.5 sampai L.11 |
| `L20_kelompok_wilayah.png` | Gambar L.12 |
| `L21_anomali_empat_wilayah_per_tahun.png` | Gambar L.13 |
| `L22_sebar_hujan_gabungan.png`, `L23_sebar_suhu_gabungan.png` | Gambar L.14 dan L.15 |
| `L24_sebar_hujan_antarwilayah.png`, `L25_sebar_suhu_antarwilayah.png` | Gambar L.16 dan L.17 |
| `L26_no2_kelas_hujan.png`, `L27_no2_kelas_suhu.png` | Gambar L.18 dan L.19 |
| `L28_sebaran_suhu_harian.png` | Gambar L.20 |
| `L29_ispu_terhadap_satelit.png` | Gambar L.21 |

Delapan peta curah hujan dan suhu udara tiap tahun (`L05` sampai `L12`) tetap
dihasilkan oleh notebook, tetapi tidak dimuat pada naskah revisi sesudah sidang
supaya lampiran tidak terlalu tebal. Karena itu penomoran gambar lampiran pada
naskah bergeser, dan lampiran naskah kini bernama Lampiran A sampai F.

Gambar 1.1, 1.2, 1.3, 2.1, dan 3.1 tidak dihasilkan di sini. Gambar 1.1 sampai 2.1
berasal dari sumber yang dicantumkan pada kapsinya, sedangkan Gambar 3.1 adalah
diagram alir yang digambar sendiri, bukan hasil pengolahan data.

Gambar di sini sama persis dengan gambar pada naskah. Lebar kanvasnya 14 cm,
selebar bidang tulis naskah, sehingga huruf di dalam gambar tercetak 8,5 sampai
9,5 pt tanpa diperkecil lagi. Gambar lampiran dipasang selebar 12 cm agar muat
tiga gambar pada satu halaman.

## Ringkas cara kerjanya

1. Kolom NO₂ harian Sentinel-5P dirata-ratakan tiap hari, petak bernilai negatif
   dibuang, lalu dipotong menurut poligon 117 kabupaten dan kota.
2. Sebelum dirata-ratakan ke batas kabupaten dan kota, NO₂ dipetakan dulu pada
   resolusi grid aslinya 0,01° memakai raster `v15_Raster_perTahun.tif`, sehingga
   keragaman di dalam satu wilayah tetap terlihat (Gambar 4.2, 4.3, dan 4.4a).
3. Untuk tiap tahun disusun tiga jendela Lebaran, yaitu arus mudik H−7 sampai H0,
   arus balik H+1 sampai H+7, dan gabungan H−7 sampai H+7, beserta periode
   acuannya, yaitu H−60 sampai H−31 dan H+30 sampai H+59.
4. Anomali tiap wilayah tiap tahun dihitung sebagai selisih jendela Lebaran
   terhadap acuan tahun itu sendiri, dinyatakan dalam persen terhadap acuan.
5. Konsistensi antartahun diuji dengan Wilcoxon berperingkat bertanda memakai
   sebaran eksak, sebab tujuh data terlalu sedikit untuk mengandaikan sebaran
   normal.
6. Keterkaitan dengan cuaca diperiksa pada dua skala, yaitu antarwilayah se-Jawa
   dan antarhari di empat wilayah kajian, dengan korelasi Pearson.
7. Curah hujan CHIRPS dan suhu udara ERA5-Land diambil untuk jendela dan acuan
   yang sama persis, sehingga dapat dipasangkan tanpa penyesuaian.
