
> **Kategori:** security

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Security_Bluetooth Security Research |
| **Nerede?** | security/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: bluetooth-security-research
description: Bluetooth guvenlik arastirma metodolojisi — akademik makale tarama, GitHub tool analizi, exploit haritasi cikarma
title: "Bluetooth Security Research"

audience: user
tags: [pentest, security]
category: security---

# Bluetooth Guvenlik Arastirma Metodolojisi

## Genel Ilke
Bluetooth guvenlik arastirmasi 3 fazda ilerler:
1. **Bilgi Toplama** — Tor ile ulke bazli arama + akademik kaynaklar
2. **Akademik Derinleme** — arXiv makalelerini indir, teknik detay cikar
3. **Yazilim Analizi** — GitHub repolarini klonla, exploit katalogu cikar

## Faz 1 — Bilgi Toplama

### Akademik Kaynaklara Erisim
```python
# arXiv API ile makale cekme (Tor gerektirmez)
url = f"https://export.arxiv.org/api/query?id_list={paper_id}"
# Analiz icin: title, summary(yazar/ozet), authors, published, category
```

### GitHub Tool Kesfi
```python
url = "https://api.github.com/search/repositories?q=..."
# Anahtar: star sayisi + guncellik + exploit cesidi
```

### Ulke Bazli Arama (Tor ile)
| Ulke | Calisan Kaynak | Bloklu |
|------|---------------|--------|
| Rusya | Habr RSS | Dogrudan HTTP |
| Cin | Kaspersky CN | CSDN, Freebuf |
| Kore | Bing KR, Naver | Boannews |
| Hindistan | GBHackers, Bing IN | SecurityWeek |

## Faz 2 — Akademik Derinleme

### arXiv Makale Is Akisi
1. **Ara:** `export.arxiv.org/api/query?search_query=...`
2. **Cek:** arXiv API XML → `get_tag("title|summary|authors|published")`
3. **Analiz et:**
   - Ozetten anahtar kelime cikar
   - Teknik yontemi belirle (binary patch, SDR, AFH manipulation vb.)
   - Gerekli donanimi cikar (RPi, HackRF, Ubertooth)
   - Ses sniffing ile ilgisi var mi? (A2DP, SCO, BLE)
4. **Siniflandir:**
   - 🔴 YUKSEK: Dogrudan ses sniffing uygulanabilir
   - 🟡 ORTA: Dolayli / BLE odakli
   - 🔵 DUSUK: Tarihsel / ilgisiz
5. **PDF baglantisi ekle:** `https://arxiv.org/pdf/{id}`

### Ozet Cikarma Sablonu
```markdown
| # | Makale | Yil | Odak | Ses? | Donanim | Uygulanabilirlik |
|---|--------|-----|------|------|---------|-----------------|
| 1 | InternalBlue | 2019 | BT Classic | ✅ | RPi + Broadcom | ⭐⭐⭐⭐⭐ |
```

## Faz 3 — Yazilim Analizi

### GitHub Repo Analiz Adimlari
1. **Klonla:** `git clone https://github.com/{author}/{repo}.git`
2. **Boyut kontrol:** `du -sh repo/`
3. **Yapi analizi:**
   - Python dosyalarini listele: `find . -name '*.py' | sort`
   - Exploit/PoC dosyalarini ayristir
   - Firmware/konfig dosyalarini bul
4. **Her exploit icin:**
   - Adi, hedef donanim, BT versiyon araligi
   - Calisma prensibi (LMP injection, ROM patch, SDR)
   - Windows/Linux uyumlulugu
5. **Katalogla:** Markdown tabloda grupla (kategori bazli)

### InternalBlue Icin Anahtar Noktalar
- Python 3.6+ gerektirir, `pip install internalblue`
- Broadcom BCM yongalari hedefler (RPi 3/4, Nexus, Samsung)
- KNOB: `lm_SendLmpEncryptKeySizeReq` fonksiyonuna `mov r2, #0x1` patch
- Key entropy 1 byte = 256 olasilik = saniyeler icinde kirilir
- A2DP ses sifrelemesi bu noktada cozulebilir

### BlueToolkit Icin Anahtar Noktalar
- Kali/Ubuntu + root gerekli (sudo ./install.sh)
- YAML tabanli exploit tanimlari (`exploits/*.yaml`)
- 4 kategori: Braktooth, InternalBlue, BlueBorne, BleedingTooth
- Hardware: Nexus5, ESP32, nRF52
- Exploit format: `bluekit run <exploit_adi> --target MAC`

### Ortak KNOB Attack Yontemi
```
1. InternalBlue ile RPi'ye baglan
2. ROM patch: key entropy = 1 byte
3. Hedef cihazla BT baglantisi kur
4. 256 olasilik brute-force
5. A2DP sifreleme cozuldu → ses akisi decode
```

## Puf Noktalari

### Referans Dosyalari
- `references/oturum-20260611.md` — 6 arXiv makalesi, 2 GitHub repo, KNOB teknik detay

- arXiv API Tor'dan erisilebilir (export.arxiv.org), diger arama motorlari bloklayabilir
- InternalBlue Windows'ta CALISMAZ — RPi veya Android gerekli
- BlueToolkit root gerekli — Windows'ta Kali VM lazim
- Adezyon: InternalBlue + Wi-Fi Saturation birlikte en guclu sonucu verir
- GitHub'da star sayisi guvenilirlik gostergesi degil, guncellik de kontrol edilmeli
