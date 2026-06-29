---
name: belirsiz-gorev-cozumu
title: Belirsiz Görev Çözümü
description: Belirsiz görev geldiğinde önce hafızayı kontrol et, en alakalı kategoriyi bul, ona göre öneri sun.
category: kullanici
Kim: ReYMeN ajani
Ne: Belirsiz görev geldiğinde önce hafızayı kontrol et, en alakalı kategoriyi bul, ona göre öneri sun.
Nerede: `reymen\belirsiz-gorev-cozumu.md`
Ne Zaman: ReYMeN sistemi yapilandirmasi gerektiginde
Neden: Belirsiz Gorev Cozumu islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Belirsiz Görev Çözümü


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ReYMeN ajani |
| **Ne** | Belirsiz görev geldiğinde önce hafızayı kontrol et, en alakalı kategoriyi bul, ona göre öneri sun. |
| **Nerede** | `reymen\belirsiz-gorev-cozumu.md` |
| **Ne Zaman** | ReYMeN sistemi yapilandirmasi gerektiginde |
| **Neden** | Belirsiz Gorev Cozumu islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar (Kali, Windows, CAD, Hermes). Kullanıcıya yanıt veren herhangi bir ajan. |
| **Ne?** | Kullanıcının belirsiz/tek kelimelik görevini analiz eder, hafızadaki en alakalı kategoriyi bulur, ona göre öneri sunar. |
| **Nerede?** | `reymen/cereyan/once_hafiza.py` → `ogrenmeler.db`. Tüm ajanlar ortak DB'yi kullanır. |
| **Ne Zaman?** | Kullanıcı "güvenli yap", "ağda sorun var", "dronu uçur" gibi net olmayan bir görev verdiğinde. |
| **Neden?** | 0 LLM çağrısı ile cevap vermek için. Hafızada varsa direkt döndür, yoksa en yakın kategoriden yönlendir. |
| **Nasıl?** | 1. `once_hafiza.ara()` ile anahtar kelime eşleştir 2. Puan = kelime×0.3 + hafiza_guven×0.7 3. En yüksek puanlı kategoriyi öner 4. Max 2 seçenek sun |

---

## Akış

```
BELİRSİZ GÖREV GELDİ
  ↓
1. HAFIZAYI KONTROL ET
   ├── once_hafiza.ara() → hafıza DB'sinde benzer kayıt
   │   - Anahtar kelimeleri çıkar
   │   - Kategori frekansı hesapla
   ├── session_search() → geçmiş konuşmalar
   └── memory() → kullanıcı tercihleri
  ↓
2. EN ALAKALI KATEGORİYİ BUL
   ├── En çok eşleşen kategori
   ├── En yüksek güven skorlu kayıt
   └── Son kullanım tarihi
  ↓
3. KULLANICIYA ÖNER
   ├── "X dedin. Hafızamda en çok Y ile ilgili kayıtlarım var."
   ├── "Z'den başlayalım mı?" (tek seçenek öner)
   └── clarify() ile onay al (max 2 seçenek)
  ↓
4. ONAY ALINDI → UYGULA
   └── HAYIR → farklı kategori dene veya açık uçlu sor
```

---

## Keyword → Kategori Eşleme Tablosu

| Kategori | Tetikleyici Kelimeler | Puan Çarpanı |
|:---------|:----------------------|:-------------|
| kali/network/nmap | güvenli, port, tarama, nmap, ağ, servis, pentest | 0.7 |
| kali/web | web, site, sql, xss, burp | 0.7 |
| cross-platform/security | koordinasyon, inter-agent, güvenlik, engelle | 0.7 |
| windows/terminal/network | windows, ipconfig, netstat, firewall | 0.7 |
| windows/terminal/system | systeminfo, tasklist, servis | 0.7 |
| dron | dron, drone, uçur, px4, uav | 0.7 |
| cad | cad, solidworks, çizim, 3d | 0.7 |
| video/python/nmap | video, python, nmap, öğren | 0.7 |

**Puan = kelime_eslesme(x0.3) + hafiza_guven(x0.7)**

---

## Örnekler

### Örnek 1: "Sistemi güvenli yap"
`once_hafiza.ara("güven")` → "güvenli" eşleşmesi → kali/network/nmap (guven=1.0)
→ "Sistemi güvenli yap dedin. Hafızamda en çok kali/network/nmap ile ilgili kayıtlarım var. Port taraması yaparak başlayalım mı?"

### Örnek 2: "Ağda bir sorun var"
`once_hafiza.ara("ağ")` → windows/terminal/network (daha yeni)
→ "Ağda bir sorun var dedin. Hafızamda windows/terminal/network ile ilgili kayıtlarım var. netstat ile bağlantıları kontrol ederek başlayalım mı?"

### Örnek 3: "Python'da nmap öğren"
"python"+"nmap" → video/python/nmap (daha spesifik)
→ "Python'da nmap öğren dedin. Hafızamda video/python/nmap ile ilgili kayıtlarım var. python-nmap kütüphanesini kurup başlayalım mı?"

---

## Kurallar

1. ASLA 4 seçenek sunma — clarify()'de max 2 choices
2. ASLA hafızayı kontrol etmeden soru sorma (once_hafiza.ara())
3. ASLA "Ne yapmak istiyorsun?" gibi açık uçlu soruyla başlama
4. Kullanıcı "hayır" derse -> 1 kez daha farklı kategori dene, yine hayir -> açık uçlu sor
5. 2. denemede bulamazsa -> "Hafızamda bu konuda kaydım yok, biraz daha detay verebilir misin?"
6. Tahmin yanlış çıkarsa -> özür dileme, direkt "Ne yapmak istemiştin?" diye sor
7. Çok fazla kategori eşleşirse -> en yüksek guven_skoru + en yeni son_kullanim

---

## Hafıza Önceliği

`once_hafiza.ara()` → `session_search()` → `memory()`
