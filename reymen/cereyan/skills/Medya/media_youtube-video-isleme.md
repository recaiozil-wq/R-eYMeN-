---
name: youtube-video-isleme
description: "YouTube URL islme merkezi. HIBRIT MOD (varsayilan): Pipeline + Rapor + Ogrenme Sorulari. 3 klasore dagitir. URL gelince dogrudan calisir."
title: "Youtube Video Isleme"
category: media
audience: user
tags: [audio, media, video]
---


> **Kategori:** media

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Video ajanı |
| **Ne?** | YouTube URL islme merkezi. HIBRIT MOD (varsayilan): Pipeline + Rapor + Ogrenme Sorulari. 3 klasore dagitir. URL gelince dogrudan calisir. |
| **Nerede?** | media/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# YouTube Video İşleme — Hibrit Mod

## Ne Yapar
Bir YouTube URL'si paylaşıldığında **otomatik hibrit mod** çalışır:

1. **Pipeline** → hermes_v7.py ile SKILL.md üret → `Ham_Analiz/`
2. **Rapor** → İçerik Bülteni + Action Items + Engellenenler + Teşekkür → `Aksiyon_Raporları/`
3. **Öğrenme Sorguları** → Sistemin kendine sorduğu pratik sorular → `Öğrenme_Sorguları/`

## Klasör Yapısı (Obsidian Vault)
```
YouTube Öğrenimler/
├── Ham_Analiz/          ← Pipeline SKILL.md'leri
├── Aksiyon_Raporları/   ← Txt raporları
└── Öğrenme_Sorguları/   ← Pratik sorular
```

## Vault Yolu
```
C:\Users\marko\OneDrive\Belgeler\Obsidian Vault\YouTube Öğrenimler\
```

## Pipeline Yolu
```
C:\Users\marko\OneDrive\Desktop\hermes_v7\hermes_v7.py
```

## Çalışma Akışı

### ADIM 1 — Pipeline'ı çalıştır
```powershell
python "C:\Users\marko\OneDrive\Desktop\hermes_v7\hermes_v7.py" --debug-video "<URL>"
```
Pipeline arka planda çalışır. Çıktı SKILL.md dosyası `hermes_v7/knowledge_base/` altında oluşur.

Pipeline bitince SKILL.md'yi `Ham_Analiz/` klasörüne kopyala.

### ADIM 2 — Aksiyon Raporu oluştur
Transkripti çek, şu formatta txt dosyası yaz:

```
═══════════════════════════════════════
İÇERİK BÜLTENİ
═══════════════════════════════════════
[Video konusu, ana akış, önemli noktalar]

═══════════════════════════════════════
UYGULANABİLİR ACTION ITEM'LAR
═══════════════════════════════════════
• [somut adım 1]
• [somut adım 2]
• ...

═══════════════════════════════════════
ENGELLENEN İÇERİKLER
═══════════════════════════════════════
[Riskli, telifli, yanlış veya uygulanamaz içerikler]

═══════════════════════════════════════
TEŞEKKÜR NOTU + İKİNCİ YOL KAYNAĞI
═══════════════════════════════════════
[Teşekkür + alternatif kaynak önerisi]
```

Dosya adı: `YYYY-MM-DD_VideoAdi.txt`
Kaydet: `Aksiyon_Raporları/`

### ADIM 3 — Öğrenme Sorguları oluştur
Video içeriğinden yola çıkarak 5-10 pratik soru üret. Sorular şunları hedeflemeli:
- İçeriği **uygulamaya** yönelik ("Bu tekniği kendi projende nasıl kullanırsın?")
- **Derinlemesine** düşündüren ("Neden bu yöntem alternatiflerinden daha iyi?")
- **Hata/çözüm** odaklı ("Hangi durumlarda bu yaklaşım çalışmaz?")

Dosya adı: `YYYY-MM-DD_VideoAdi_Sorular.md`
Kaydet: `Öğrenme_Sorguları/`

Format:
```markdown
# Öğrenme Sorguları — [Video Başlığı]

## Uygulama Soruları
1. ...
2. ...

## Analiz Soruları
1. ...
2. ...

## Hata/Çözüm Soruları
1. ...
2. ...
```

### ADIM 4 — Kullanıcıya raporla

```
✓ Video işlendi: [başlık]

  📄 Ham Analiz → YouTube Öğrenimler/Ham_Analiz/[dosya]
  📋 Aksiyon Raporu → YouTube Öğrenimler/Aksiyon_Raporları/[dosya]
  ❓ Öğrenme Sorguları → YouTube Öğrenimler/Öğrenme_Sorguları/[dosya]

  Güven: [skor]/100
  Süre: [X] dk
```

## Alternatif Modlar

| Kullanıcı ne derse | Ne yap |
|---|---|
| Sadece URL (açıklama yok) | **Hibrit mod** (varsayılan) — pipeline + rapor + sorgu |
| "Sadece pipeline çalıştır" | Sadece ADIM 1 — Ham_Analiz/ |
| "Sadece rapor çıkar" | Sadece ADIM 2 — Aksiyon_Raporları/ |
| "Sadece soru üret" | Sadece ADIM 3 — Öğrenme_Sorguları/ |
| "Özet yap", "transkript al" | youtube-content skill'ine yönlendir |
| **Özel talimat** ("belirle ve skill oluştur", "analiz et ve öner", "teknik stack çıkar" vb.) | Kullanıcının tarifine göre işle. Pipeline yerine kullanıcının talebini takip et. Video içeriğini analiz et, talep edilen formatta çıktı üret. |
| **Video serisi** ("bu ve 1 tane daha var", "buda son video", aynı seriden 2+ video) | **Kümülatif mod:** Tüm videoları sırayla işle, her birini aynı skill dosyasına alt bölüm olarak ekle. Her video için ayrı references/<video-N>-<seri>.md referans dosyası oluştur. Skill'in girişindeki referans tablosunu her yeni videoda güncelle. Son videoda "tümü kaydet" denmişse ayrıca sistem taraması + proje önerisi yap. |

## Hata Yönetimi
- Pipeline çalışmazsa: hatayı logla, kullanıcıya bildir, ADIM 2 ve 3'ü transcript üzerinden dene
- Pipeline için önce youtube-transcript-api'yi dene (tercih edilen yöntem):
  ```python
  from youtube_transcript_api import YouTubeTranscriptApi
  api = YouTubeTranscriptApi()
  transcript = api.fetch(video_id, languages=['tr','en'])
  full_text = ' '.join([s.text for s in transcript])
  ```
  NOT: `get_transcript()` classmethod'u kaldırıldı — yeni API `().fetch()`.
  Uzun videolarda (~1 saat) tek seferde çek, sonra ~500 kelimelik chunk'lara böl.
  Bu yöntem browser/web_extract'tan daha hızlı ve güvenilir.
- Pipeline ve youtube-transcript-api de başarısız olursa: tarayıcıyı dene (browser_navigate + browser_console ile)
- Son çare: video başlığı + açıklamasından rapor çıkarmayı dene
- Video özel/kullanılamıyorsa: "Video alınamadı" de, geç

## Tuzaklar (Pitfalls)

### Pipeline "başarılı" döndü ama içerik anlamsız
Pipeline `"success": true` döndüğü halde görüntü analizi (llava/vlm model) videoyla ilgisiz içerik üretebilir.
**Belirti:** Pipeline çıktısı SKILL.md'deki özet, videonun konusuyla alakasız (ör: Dario Amodei videosu için "breakpoint kullanımı" çıktısı).

**Çözüm:** Pipeline çıktısını her zaman transkriptle doğrula:
  1. Pipeline'dan gelen SKILL.md'yi aç, içerik videoyla tutarlı mı kontrol et
  2. Tutarsızsa pipeline çıktısını yine `Ham_Analiz/`'e kaydet (referans olarak) ama **rapor ve sorguları transkriptten oluştur**
  3. Kullanıcıya raporlarken pipeline'ın görüntü analizinin zayıf olduğunu belirt

### yt-dlp eksik olduğunda pipeline çöker
Pipeline `pip install yt-dlp` gerektirir. Eksikse `"Video indirilemedi"` hatası döner.
**Çözüm:** Global pip'ten yükle (`pip install yt-dlp`), pipeline'ı yeniden çalıştır.

### Transkript API sürüm uyumsuzluğu
Eski kod (`get_transcript()`) `AttributeError: type object has no attribute 'get_transcript'` hatası verir.
**Çözüm:** `YouTubeTranscriptApi().fetch(video_id, languages=['tr','en'])` kullan, çıktıyı `' '.join([s.text for s in transcript])` ile birleştir.

## Kullanıcı Profili
- Kullanıcı YouTube videolarından öğrenip Hermes'e özellik eklememi ister
- Çıktıları Obsidian vault'ta düzenli görmek ister
- Hata durumunda alternatif çözümle devam etmemi bekler
- Sormamı değil, çözüp raporlamamı ister