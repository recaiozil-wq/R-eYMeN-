---
name: otonom-gece-gelistirme
title: "Otonom Gece Gelistirme"
tags: [agents, ai]
description: >
  Gece boyunca çalışan otonom geliştirme döngüsü. Obsidian vault'u tara,
  eksik skill'leri bul, yeni skill oluştur, mevcutları güncelle/geliştir,
  sonucu Telegram'a raporla.
version: 2.2.0
author: hermes-agent
license: MIT
metadata:
  hermes:
    tags: [nightly, autonomous, self-improvement, cron, obsidian, skill-maintenance]
audience: user
related_skills: [obsidian-vault-kurallari, nightly-self-improvement, hermes-agent, telegram-gateway-monitor]


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | > |
| **Nerede** | `autonomous-ai-agents\autonomous-ai-agents_otonom-gece-gelistirme.md` |
| **Ne Zaman** | Ilgili gorev gerektiginde |
| **Neden** | Autonomous Ai Agents Otonom Gece Gelistirme islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | > |
| **Nerede?** | autonomous-ai-agents/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: Otonom ajan gelistiricisi
Ne: >
Nerede: `autonomous-ai-agents\autonomous-ai-agents_otonom-gece-gelistirme.md`
Ne Zaman: Ilgili gorev gerektiginde
Neden: Autonomous Ai Agents Otonom Gece Gelistirme islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Otonom Gece Geliştirme Döngüsü

## Amaç

Bu cron job, gece 02:00-05:00 arası otomatik olarak çalışır. Hermes'in skill kütüphanesini
ve Obsidian vault'u tarar, geliştirme fırsatlarını belirler ve uygular.

## Zorunlu Adımlar (sıralı)

### 1. Ortam Kontrolü

```bash
ls "/c/Users/marko/OneDrive/Belgeler/Obsidian Vault" 2>&1 || echo "VAULT_YOK"
hermes skills list 2>&1
hermes cron list 2>&1
```

### 2. Obsidian Vault Taraması

Tüm `Hermes/Skills/` altındaki notları tara:

```bash
find "/c/Users/marko/OneDrive/Belgeler/Obsidian Vault/Hermes/Skills" -name "*.md" | wc -l
```

Kontrol edilecekler:
- Hangi skill kategorileri mevcut?
- Skill notlarında güncellenmesi gereken yol/URL hataları var mı?
- `C:\Users\marko\Documents\` yerine yanlış yollar kullanılıyor mu?

### 3. Skill + Obsidian Fark Analizi

Doğrudan dosya sistemi taraması kullan — `skills list --json` desteklenmiyor.

```python
# Hermes skill'leri: skills/ altındaki tüm SKILL.md'leri tara
find "/c/Users/marko/AppData/Local/hermes/skills" -name "SKILL.md"

# Obsidian notları: Hermes/Skills/ altındaki .md'leri tara (indeks hariç)
find "C:/Users/marko/OneDrive/Belgeler/Obsidian Vault/Hermes/Skills" -name "*.md" -not -name "_*"
```

Karşılaştırma:
1. `skills_list()` ile tüm Hermes skill'lerini al (kategorili liste)
2. Obsidian'daki skill notlarıyla karşılaştır (find ile)
3. Şunları tespit et:
   - **Eksik skill**: Hermes'te var ama Obsidian'da yok → Obsidian'a kaydet
   - **Eksik Obsidian notu**: Obsidian'da var ama Hermes'te yok → yeni skill oluştur
   - **Güncellenmesi gereken**: yol hataları, eski referanslar, yanlış kategoriler
   - **Çakışan skill adları**: duplicate kontrol
   - **Cleanup klasörleri**: `__cleanup_*` ve `___cleanup_*` öneklerini fark analizinden hariç tut
   - **İsim çakışmaları**: Aynı skill farklı isimle kayıtlıysa tespit et
     (örn: Hermes `audiocraft` = Obsidian `audiocraft-audio-generation`)
     **Bilinen çakışmalar için** `self-improvement` skill'inin
     `references/name-clash-map.md` dosyasına bak — 8 adet önceden tespit edilmiş
     çakışma kayıtlıdır.

Not: `hermes skills list --json` çalışmaz — CLI output'u ayrıştırması zordur.
Dosya sistemi taraması daha güvenilirdir.

Fark analizi için `comm` komutu + normalize isim karşılaştırması kullan:

```bash
# 1. Hermes skill adlarını çıkar (cleanup hariç)
find "/c/Users/marko/AppData/Local/hermes/skills" -name "SKILL.md" | grep -v "__cleanup" | while read f; do
  basename "$(dirname "$f")"
done | sort -u > /tmp/hermes_flat.txt

# 2. Obsidian not adlarını çıkar (indeks ve cleanup hariç)
find "/c/Users/marko/OneDrive/Belgeler/Obsidian Vault/Hermes/Skills" -name "*.md" \
  -not -name "_*" -not -path "*/__cleanup*" | while read f; do
  basename "$f" .md
done | sort -u > /tmp/obsidian_flat.txt

# 3. Karşılaştır
echo "=== HERMES-ONLY (Obsidian'da yok) ==="
comm -23 /tmp/hermes_flat.txt /tmp/obsidian_flat.txt
echo "=== OBSIDIAN-ONLY (Hermes'te yok) ==="
comm -13 /tmp/hermes_flat.txt /tmp/obsidian_flat.txt
```

### 4. Skill Geliştirme/Güncelleme

Her skill için sırayla:

1. `skill_view(name)` ile oku — başarısız olursa skill hatalıdır
2. Şunları kontrol et:
   - `related_skills` doğru mu?
   - Yol/URL hataları var mı?
   - `Pitfall'lar` bölümü var mı?
   - `Başarı Kriterleri` bölümü var mı?
3. Eksik varsa `skill_manage(action='patch')` ile düzelt
4. Yeni bir teknik/çözüm bulunduysa içeriğe ekle

### 5. Yeni Skill Oluşturma (Opsiyonel)

Obsidian'da yeni bir not tespit edilirse ve Hermes skill'i yoksa:

1. İçeriğini oku ve analiz et
2. Uygun kategori belirle
3. SKILL.md formatında `skill_manage(action='create')` ile oluştur
4. Obsidian'a Hermes/Skills/ altına kaydet

### 6. Rapor (Otomatik Teslim)

Cron job modunda son yanıt otomatik olarak teslim edilir. Rapor formatı:

```
[gece-gelistirme] <tarih-saat>
├── Tarama: N skill, N Obsidian notu
├── Güncellenen: N skill
├── Oluşturulan: N yeni skill
├── İsim çakışmaları: N adet
└── Sorun: varsa buraya
```

Eğer hiçbir şey değişmemişse (yeni skill yok, güncelleme yok, sorun yok):
- Son satırda `[SILENT]` yanıtı ver (bildirim gönderilmez)
- Asla `[SILENT]` ile içeriği birleştirme

`.env` token kontrolü:
- `grep TELEGRAM_BOT_TOKEN /c/Users/marko/AppData/Local/hermes/.env`
- Token `***` içeriyorsa maskelenmiş demektir — düzeltme yapma, kullanıcıya bildir

### 7. Obsidian Çalışma Kaydı

Çalışma kaydını şuraya ekle:

```
C:\Users\marko\OneDrive\Belgeler\Obsidian Vault\Hermes\Cron\gece-gelistirme.md
```

Her çalışma **en üste** yeni bir bölüm olarak eklenir (prepend — append değil).
Format:

```markdown
## <tarih> <saat>

### Yapılanlar
- ...

### Sorunlar
- ...

### Notlar
- ...
---

## Pitfall'lar

- **Telegram token maskelenmesi**: `.env`'de `TELEGRAM_BOT_TOKEN=...***...` varsa gateway çalışmaz.
  Bunu tespit et ama düzeltme — kullanıcıya bildir.
- **Duplicate skill adları**: Aynı isimde iki skill varsa `skill_view()` hata verir.
  Tam kategorili yol kullan: `kategori/skill-adi`
- **Obsidian yanlış yol**: `C:\\Users\\marko\\Documents\\` yolu hatalıdır, doğrusu
  `C:\\Users\\marko\\OneDrive\\Belgeler\\Obsidian Vault`
- **Cron delivery çakışması**: İki cron job aynı anda aynı Telegram hedefine gönderirse
  ikisi de çalışır ama raporlar karışabilir.
- **Uzun çalışma süresi**: 3+ saat sürebilir. `timeout` değerini yüksek tut (600+ sn).
- **Python venv yok**: `C:/Users/marko/AppData/Local/hermes/venv/Scripts/python.exe` mevcut
  değil. System Python kullan: `C:/Users/marko/AppData/Local/Python/PythonCore-3.14-64/python.exe`
- **`hermes` CLI output parse**: `hermes skills list --json` desteklenmez. Skill listesi
  için `skills_list()` kullan veya dosya sistemi tara.
- **Cleanup klasörleri atlanır**: `__cleanup_*` ile başlayan skill klasörleri fark
  analizinde yok sayılmalı.
- **sync_skills_to_obsidian.py**: `C:\Users\marko\AppData\Local\hermes\hooks\` altındadır.
  System Python ile çalıştırılmalıdır. `pyyaml` bağımlılığı gerekir.
  Çıktısı: "Yazilan: N / M skill" (her çalıştırmada sadece yeni/yazılmayanları yazar)

- **İsim çakışmaları**: Hermes adı ≠ Obsidian adı olan skill'ler için `Hermes/isim-cakismalari.md` referans notu güncellenmeli. Eşleme tablosu elle tutulur (sync scripti YAML frontmatter'daki skill_name ile eşleme yapar, dosya adı farkını tolere eder).

## Başarı Kriterleri

- ✓ Obsidian vault tarandı ve skill sayısı raporlandı
- ✓ Tüm Hermes skill'leri okundu ve durumları kontrol edildi
- ✓ En az bir güncelleme/yeni skill oluşturma yapıldı (veya "yapılacak bir şey yok" raporlandı)
- ✓ Telegram'a eksiksiz rapor gönderildi
- ✓ Obsidian vault'a çalışma kaydı eklendi
