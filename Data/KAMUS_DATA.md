# Kamus data

Seluruh berkas pada `01_mentah` adalah data masukan: sepuluh berkas hasil ekspor
Google Earth Engine dan satu berkas data terbuka Pemerintah Provinsi DKI Jakarta.
Berkas pada `02_olahan` dihasilkan oleh notebook dan boleh dihapus kapan saja,
sebab akan dibuat ulang setiap notebook dijalankan.

Kode `v11`, `v13`, dan seterusnya adalah nomor urut ekspor selama penelitian.
Penomoran itu dipertahankan supaya nama berkas di sini sama persis dengan nama
tugas ekspor pada Earth Engine.

## Sumber data

| Data | Sumber | Aras waktu | Resolusi asli | Dipakai untuk |
|---|---|---|---|---|
| NO₂ troposferik | Sentinel-5P TROPOMI, koleksi `COPERNICUS/S5P/OFFL/L3_NO2`, pita `tropospheric_NO2_column_number_density` | harian, lintasan pukul 13.30 waktu setempat | 3,5 × 5,5 km (3,5 × 7 km sebelum 6 Agustus 2019) | seluruh perhitungan NO₂ |
| Curah hujan | CHIRPS, koleksi `UCSB-CHG/CHIRPS/DAILY`, pita `precipitation` | harian | 0,05° atau sekitar 5,5 km | peubah meteorologi |
| Suhu udara | ERA5-Land, koleksi `ECMWF/ERA5_LAND/DAILY_AGGR`, pita `temperature_2m` | harian | 0,1° atau sekitar 11 km | peubah meteorologi |
| Batas wilayah | FAO GAUL 2015 aras 2, koleksi `FAO/GAUL/2015/level2` | — | poligon | membagi Jawa menjadi 117 kabupaten dan kota |
| Indeks ISPU NO₂ | Data terbuka Pemerintah Provinsi DKI Jakarta, indeks standar pencemar udara 2022 | harian | lima stasiun DKI | pembanding dengan pengamatan permukaan |

Seluruh berkas Earth Engine dihasilkan oleh `Script/ambil_data_gee.py`. Nama tugas
ekspor pada skrip itu sama dengan nama berkas di sini.

## Berkas pada 01_mentah

### v11_NO2_perKabupaten_500m.csv
Nilai NO₂ tiap periode tiap tahun untuk 117 kabupaten dan kota. Satu baris satu
wilayah.

| Kolom | Arti |
|---|---|
| `ADM1_NAME`, `ADM2_NAME` | nama provinsi dan nama kabupaten atau kota menurut FAO GAUL |
| `ADM0_CODE` … `Shape_Leng` | keterangan bawaan FAO GAUL, `Shape_Area` dipakai menghitung luas |
| `acA` | acuan A, rerata H−325 sampai H−31 untuk tujuh tahun |
| `acD_2019` … `acD_2025` | acuan D, rerata H−60 sampai H−31 dan H+30 sampai H+59 pada tahun itu. **Inilah acuan yang dipakai di naskah** |
| `acE_2019` … `acE_2025` | acuan E, bulan Masehi tempat Idul Fitri jatuh, tanpa jendela Lebaran |
| `mudik_2019` … | rerata arus mudik, H−7 sampai H0 |
| `balik_2019` … | rerata arus balik, H+1 sampai H+7 |
| `gab_2019` … | rerata gabungan, H−7 sampai H+7 |
| `.geo` | poligon wilayah dalam GeoJSON, dipakai menggambar peta |

Satuan seluruh kolom nilai: mol/m². Pada pengolahan dikalikan 10⁵ sehingga
disajikan sebagai ×10⁻⁵ mol/m². Petak dengan kolom negatif dibuang sebelum
perataan, bukan dijadikan nol.

Skala pencuplikan 500 m dipakai karena delapan kota kecil, antara lain Kota Cimahi
dan Kota Magelang, lebih sempit daripada satu petak 1113 m sehingga pada skala asli
tidak ada pusat petak yang jatuh di dalamnya dan hasilnya kosong. Nilainya tetap
berasal dari petak 1113 m yang sama.

### v11_Hujan_perKabupaten_CHIRPS.csv dan v11_Suhu_perKabupaten_ERA5Land.csv
Susunan kolomnya sama persis dengan berkas NO₂, untuk jendela dan acuan yang sama.
Curah hujan dijumlahkan lalu dibagi jumlah hari jendelanya, jadi satuannya mm per
hari dan dapat dibandingkan antarjendela. Suhu dirata-ratakan dan masih dalam
kelvin.

### v13_Harian_NO2.csv, v13_Harian_Hujan.csv, v13_Harian_Suhu.csv
Deret harian untuk wilayah kajian, H−60 sampai H+59 tiap tahun, 2019 sampai 2025.

| Kolom | Arti |
|---|---|
| `tanggal` | YYYY-MM-DD |
| `wilayah` | Kota Surabaya, Purbalingga, Ponorogo, Kota Jakarta Timur |
| `nilai` | NO₂ dalam ×10⁻⁵ mol/m², hujan dalam mm, suhu dalam °C |

Sel kosong pada berkas hujan berarti hari tanpa hujan, bukan data hilang; pada
pengolahan diisi nol. Sel kosong pada NO₂ berarti tidak ada petak lolos saring
pada hari itu, umumnya karena awan, dan hari itu dilewati.

### v18_NO2_Periode_DKI.csv dan v18_Harian_DKI.csv
Sama seperti v11 dan v13, tetapi DKI Jakarta digabung menjadi satu wilayah, sebab
sejak bimbingan 15 September DKI dipakai utuh satu provinsi, bukan salah satu kota
administrasinya. Kota Jakarta Timur ikut diekspor sebagai pembanding; nilainya
harus sama dengan berkas v11 dan v13, dan itu sudah diperiksa.

### v16_NO2_Bulanan_perKabupaten.csv
Rerata NO₂ tiap bulan untuk tiap wilayah. Kolom `b2019_01` sampai `b2025_12`,
satuannya mol/m².

### v14_ISPU_DKIJakarta_2022.csv
Indeks standar pencemar udara harian DKI Jakarta tahun 2022. Kolom yang dipakai
hanya `tanggal` dan `no2`. Berkasnya bukan per stasiun, melainkan nilai harian
provinsi, dan lokasi stasiun penentunya berganti antarhari; keterbatasan ini
disebut di naskah.

### v15_Raster_perTahun.tif
Peta NO₂ yang belum dirata-ratakan ke batas administratif, dipakai untuk Gambar 4.2,
4.3, dan panel (a) Gambar 4.4. Berkas GeoTIFF dengan grid 0,01°, yaitu grid asli
produk L3 Earth Engine.

| Keterangan | Nilai |
|---|---|
| Ukuran | 951 kolom × 324 baris × 28 pita, bilangan pecahan 32 bit |
| Titik ikat petak pertama | bujur 104,99048025385159 dan lintang −5,590025570235549 |
| Lebar petak | 0,010000045742818514 derajat |
| Urutan pita | tiap tahun empat pita berurutan, yaitu acuan D, gabungan, arus mudik, dan arus balik |
| Nomor pita | 4 × (tahun − 2019) + 0 untuk acuan D, + 1 gabungan, + 2 arus mudik, + 3 arus balik |
| Satuan | mol/m², dikalikan 10⁵ pada pengolahan |

Petak di luar daratan Jawa dan petak tanpa pengamatan bernilai kosong. Pada skrip,
daratan ditandai memakai poligon provinsi dari `v5_Batas_Provinsi_Jawa.geojson`,
sehingga petak kosong di dalam daratan tidak terbaca sebagai laut.

### v5_Batas_Provinsi_Jawa.geojson
Enam poligon provinsi, hasil penggabungan poligon kabupaten dan kota. Dipakai
menggambar garis pantai dan garis batas provinsi pada peta.

## Berkas pada 02_olahan

Seluruhnya dihasilkan notebook.

| Berkas | Isi |
|---|---|
| `harian_no2.csv`, `harian_hujan.csv`, `harian_suhu.csv` | deret harian gabungan, Kota Jakarta Timur diganti DKI Jakarta |
| `T4_1_perubahan_empat_wilayah.csv` | Tabel 4.1 |
| `T4_2_ringkasan_uji_cuaca.csv` | Tabel 4.2, sepuluh uji korelasi |
| `TL_1_perubahan_sejawa_periode.csv` | Tabel L.1 |
| `TL_2_anomali_sejawa_tiap_tahun.csv` | Tabel L.2 |
| `TL_3_perbandingan_tiga_acuan.csv` | Tabel L.3 |
| `TL_4_perubahan_kelompok_wilayah.csv`, `TL_4b_anggota_kelompok.csv` | Tabel L.4 beserta daftar anggotanya |
| `TL_5_peringkat_anomali.csv` | Tabel L.5 |
| `TL_6_luas_dan_cacah_petak.csv` | Tabel L.6 |
| `anomali_gabungan_117_wilayah.csv` | anomali tiap wilayah tiap tahun |
| `deret_harian_empat_wilayah.csv` | angka di balik Gambar 4.7 sampai 4.9 |
| `rerata_bulanan_sejawa.csv` | angka di balik Gambar 4.1 |
| `ringkasan_angka.json` | seluruh angka utama dalam satu berkas |
