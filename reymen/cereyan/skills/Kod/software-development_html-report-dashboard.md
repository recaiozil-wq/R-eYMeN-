
> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Software Development_Html Report Dashboard |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
title: "HTML Report Dashboard"
description: "Edit, debug, and maintain self-contained HTML report dashboards with embedded JS libraries (Chart.js, SheetJS/XLSX, chartjs-plugin-datalabels)."
trigger: "User references an .HTM or .HTML file with embedded Chart.js/XLSX libraries, or asks to fix numbers/tables/charts in a self-contained HTML report."
name: html-report-dashboard

audience: contributor
tags: [coding, development]
category: software-development---

# HTML Report Dashboard — Edit & Debug Guide

Self-contained HTML rapor dosyalari (`*.HTM` / `*.html`), Chart.js, SheetJS ve chartjs-plugin-datalabels gibi kutuphaneleri `<script>` tag'lari icinde gomulu tasir. Bu kilavuz, bu tur dosyalarda duzenleme yaparken dikkat edilmesi gerekenleri icerir.

## Yapi

Tipik bir self-contained dashboard:

```
<!DOCTYPE html>
<html>
<head>
  <script>/* Chart.js v4 gomulu */</script>
  <script>/* chartjs-plugin-datalabels gomulu */</script>
  <script>/* SheetJS xlsx.js gomulu */</script>
  <style> /* Koyu tema CSS */ </style>
</head>
<body>
  <!-- Navigasyon + icerik alani -->
  <script> /* Uygulama mantigi (COLS, build fonksiyonlari, chart helpers) */ </script>
</body>
</html>
```

## Patch Araci ile Calisirken — KACIS KARAKTERI TUZAGI

**Bu en kritik bolumdur.** Patch araci HTML/JS dosyalarinda `\'` gibi kacis karakterlerini duzgun islemeyebilir.

### Sorun
HTML/JS dosyalarinda sik kullanilan `\'` (JS'de escaped single quote) deseni, patch araci tarafindan yanlis yorumlanabilir:
- Orijinal: `'...2\'nci...'` (JS string, `\'` = `'` karakteri)
- Patch sonrasi: `'...2\\'nci...'` (BOZUK - JS syntax hatasi!)

Bozuk JS'de:
- `'...2\\'` -> string `...2\` (escaped backslash)
- `'` -> string sonlandirici
- `nci` -> identifier -> **SYNTAX ERROR**

### Cozum
1. Patch araci kacis karakterlerini bozarsa, **dosyayi binary mode'da Python ile duzelt**:

```python
with open('path/to/file.HTM', 'rb') as f:
    data = f.read()
data = data.replace(b"2\\\\'nci", b"2\\'nci")
with open('path/to/file.HTM', 'wb') as f:
    f.write(data)
```

2. En guvenlisi: **kritik degisiklikleri Python veya direkt terminal komutu ile yap**, patch aracini kullanma.

### Tespit
JS syntax hatasi olustugunda tarayici konsolunda hata gorunur ve "dosya yuklenmiyor" hatasi alinir. Belirtiler:
- XLSX kutuphanesi yuklenir ama `onAllLoaded()` cagrilmaz
- "Dosya Yukle" butonuna basinca hicbir sey olmaz
- Tarayici konsolunda `Unexpected identifier` veya `SyntaxError` hatasi

## Veri Sutunu Tutarliligi

### Kritik Kural
**Yorum metni ve grafik/pasta grafik AYNI veri sutununu kullanmalidir.** Farkli sutunlar kullanilirsa sayilar tutarsiz olur.

Ornek hata: Pasta grafik `INCELEME MERKEZI` sutunundan okurken, yorum metni `IMALAT YERI` veya `ONARIM YERI` sutunundan okuyor.

### Du zeltme
Her iki fonksiyonda da ayni sutun referansini kullan:
```javascript
var INCELEME_COL = COLS.INCELEME; // tek kaynak
```

### generateCommentary vs buildIncelemeYeriPane
Bu iki fonksiyon ayni veriyi farkli formatlarda sunar:
- `generateCommentary()` -> Home sayfasindaki 5 maddelik resmi rapor yorumu
- `buildIncelemeYeriPane()` -> B1-3 sayfasindaki tablo + pasta + alt yorum

Ikisi de ayni `INCELEME MERKEZI` sutununu kullanmali.

## Grafik Renkleri vs Tablo Renkleri

Pasta grafikteki renk paleti:
- `#3399ff` (mavi) -> 2'nci HBF Md.lugu
- `#ff7043` (turuncu) -> Yurt Disi
- `#66bb6a` (yesil) -> Yurt Ici Firma

Tablodaki satirlar bu renklerle eslesmelidir. Her satirin:
- `background: rgba(R,G,B,.1)` - soluk ton
- `border-left: 3px solid #RRGGBB` - sol tarafta renkli cubuk

## CSS Renklendirme

Sayilara altin sari renk vermek icin:
```css
.cc p b{color:var(--gold2)}
```

Bu CSS degisikligi JS syntax'ini etkilemez - guvenle eklenebilir.

## Test Proseduru
1. Du zeltme sonrasi dosyayi tarayicida **F5** ile yenile
2. XLSX dosyasini yukle - hata yoksa badge'ler guncellenir
3. Home sayfasindaki yorum metnini kontrol et
4. B1-3 sayfasindaki pasta grafik + tablo + yorum tutarliligini kontrol et
5. Tarayici konsolunda (F12) JS hatasi olmadigini dogrula
