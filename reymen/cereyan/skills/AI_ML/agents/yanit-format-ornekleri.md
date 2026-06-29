
> **Kategori:** references

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Yanit Format Ornekleri |
| **Nerede?** | references/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Yanit Format Ornekleri — Cave Mode

## Kiral38 Format (Canli Fiyat/Veri Sorulari)

Kullanici fiyat/veri sordugunda @Kiral38bot formatini birebir uygula.

**Zorunlu alanlar:** Kaynak adi + URL + fiyat, Fiyat Uyumu satiri + emoji, Ortalama.

### Dogru format:
```
🥇 Altin Ons (XAU/USD) — Canli

Kaynaklar:
- Investing.com → $4.153,71 — $4.155,24
- Paratic → $4.155,55
- Bigpara → $4.155,29 — $4.155,83

Fiyat Uyumu: ✅ Tutarli — 3 kaynak arasinda max $2 fark ($4.153 — $4.155). Piyasa sakin.

Ortalama: ~$4.155
```

### Adimlar (sirayla)
1. **Kaynak tara** — web_search/web_extract ile canli veri. Her kaynagin URL'sini not et.
2. **Yaz** — Emoji baslik + "Kaynaklar:" alt basligi
3. **Listele** — Her kaynak icin `- KaynakAdi [URL](link) → $fiyat`. OK istemezse URL'siz de yaz.
4. **Uyum kontrolu** — Fiyatlar tutarli mi, fark var mi? Yorumla. Emoji kullan.
5. **Ortalama** — son satir: `Ortalama: ~$deger`

### Emojiler
| Emoji | Anlami |
|:-----:|:-------|
| ✅ | Tutarli (fark < %1) |
| ⚠️ | Kucuk fark (%1-3) |
| 🔴 | Buyuk fark (>%3) |
| 🔵 | Tek kaynak — karsilastirma yok |

### Pitfall — URL'siz kaynak gosterme
Kullanici URL de istemezse "Kaynaklar:" satirinda sadece isim yaz, link koyma. Ama URL'yi hafizanda tut (sorgulanirsa cevap ver).

### Ornek 2 — Birden cok emtia:
```
🥇 Altin: $X.XXX  |  💰 Gumus: $XX,XX  |  🛢 Petrol: $XX,XX
Kaynak: [Investing.com](https://...)
Fiyat Uyumu: ✅ 3 emtia da ayni kaynaktan
```
