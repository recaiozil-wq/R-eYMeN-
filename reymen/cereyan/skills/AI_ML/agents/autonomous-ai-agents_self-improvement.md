---
name: self-improvement
title: "Hermes Otonom Geliştirme Gece Rutini"
description: "Hermes'in geceleri kendi kendine Obsidian vault + Hermes skills tarayarak gelişmesi: eksik notları skill'e dönüştür, güncel olmayan skill'leri güncelle, isim çakışmalarını çöz, senkronizasyonu doğrula."
tags: [self-improvement, otomatik-bakim, skill-audit, obsidian-sync, gece-rutini]
category: autonomous-ai-agents
audience: user
related_skills: [obsidian-vault-kurallari, skill-cataloging, env-kayit-kurallari]
triggers: [self-improvement, gece bakimi, skill gelistir, otomatik gelisme]


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | "Hermes'in geceleri kendi kendine Obsidian vault + Hermes skills tarayarak gelişmesi: eksik notları skill'e dönüştür, güncel olmayan skill'leri güncelle, isim çakışmalarını çöz, senkronizasyonu doğrul |
| **Nerede** | `autonomous-ai-agents\autonomous-ai-agents_self-improvement.md` |
| **Ne Zaman** | Ilgili gorev gerektiginde |
| **Neden** | Autonomous Ai Agents Self Improvement islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Hermes'in geceleri kendi kendine Obsidian vault + Hermes skills tarayarak gelişmesi: eksik notları skill'e dönüştür, güncel olmayan skill'leri güncelle, isim çakışmalarını çöz, senkronizasyonu doğrula. |
| **Nerede?** | autonomous-ai-agents/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: Otonom ajan gelistiricisi
Ne: "Hermes'in geceleri kendi kendine Obsidian vault + Hermes skills tarayarak gelişmesi: eksik notları skill'e dönüştür, güncel olmayan skill'leri güncelle, isim çakışmalarını çöz, senkronizasyonu doğrul
Nerede: `autonomous-ai-agents\autonomous-ai-agents_self-improvement.md`
Ne Zaman: Ilgili gorev gerektiginde
Neden: Autonomous Ai Agents Self Improvement islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Hermes Otonom Geliştirme — Gece Rutini

## Görev Sırası

### 1. Obsidian Vault Tara
- `C:\Users\marko\OneDrive\Belgeler\Obsidian Vault` altındaki tüm .md dosyalarını tara
- Konuları ve bilgileri kategorize et
- Eksik skill olabilecek notları tespit et (özellikle `Hermes\Skills\` dışındakileri de oku — orada kaliteli notlar olabilir)

### 2. Mevcut Skill'leri Tara
- `C:\Users\marko\AppData\Local\hermes\skills\` altındaki tüm SKILL.md dosyalarını oku (rglob)
- Ayrıca root seviyesinde `.md` dosyası olup SKILL.md dönüşümü yapılmamış olanları da tespit et
- Güncel olmayan, eksik veya geliştirilebilir skill'leri belirle

### 3. İsim Çakışmalarını Çöz

**Önce referans haritayı oku:** `references/name-clash-map.md` — 8 bilinen çakışma
kayıtlıdır. Bu liste dışında yeni bir Hermes-only adı varsa, Obsidian'da benzer
isim ara ve haritaya ekle.
- `skill_view()` "Ambiguous skill name" hatası veriyorsa: hem root'ta `.md` hem de `kategori/alt-skill/SKILL.md` var demektir
- Önce proper SKILL.md'in içeriğini oku, eski .md sadece frontmatter+2 satır mı yoksa daha dolu mu kontrol et
- Eski .md daha az detaylıysa: rename et → `<eski-ad>.md.obsolete` (rm kullanma, approval gerekir)
- **Root-level skill dizini kopyası varsa** (örn. `skills/telegram-gateway-monitor/` vs `skills/autonomous-ai-agents/telegram-gateway-monitor/`):
  - `mcp_filesystem_move_file()` ile root kopyayı `__cleanup_deprecated_<skill-adi>` adına taşı
  - SKILL.md'i `.deprecated` uzantısı yap (böylece runtime tarafından okunmaz)
  - NOT: Dosya sistemi taşıma `skills_list` index'ini güncellemez. Tam yeniden yükleme (`/reload-skills` veya agent restart) gerekir.
- Sync edilmiş proper SKILL.md'in eksiksiz olduğunu doğrula

### 3b. Kategori Kuralları
- `skill_manage` kategorileri TEK DÜZEY olabilir: `mlops` ✓, `mlops/inference` ✗
- Geçerli karakterler: lowercase harfler, sayılar, tire, nokta, alt çizgi
- Kategori kök dizin adı olur: `skills/<kategori>/<skill-adi>/SKILL.md`

### 4. Karşılaştır ve Geliştir
- Obsidian'da olup skill olarak yazılmamış konular → yeni skill oluştur (`skill_manage create`)
- Mevcut skill'lerde eksik adımlar → güncelle (`skill_manage patch` veya `edit`)
- **Skill kalite taraması** — Tüm skill'leri tara ve şu metrikleri raporla:
  - `Pitfall'lar` bölümü olan skill sayısı
  - `Başarı Kriterleri` bölümü olan skill sayısı
  - `related_skills` alanı boş olan skill sayısı
  Arama: `search_files(pattern="## Pitfall", target="content", path="AppData/Local/hermes/skills")` ve `search_files(pattern="Başarı Kriterleri", target="content", path="AppData/Local/hermes/skills")` — eğer 80+ skill'de Pitfall yoksa bu büyük bir kalite boşluğudur ve raporun ana maddesi olmalıdır.
- **Windows path hygiene kontrolü** — Skill SKILL.md'lerinde eski/yaygın hatalı yolları tara:
  - `~/Documents/Obsidian Vault` → `C:\\Users\\marko\\OneDrive\\Belgeler\\Obsidian Vault`
  - `Documents\\Obsidian Vault` (tam yol olmadan) → düzelt
  - `C:\\Users\\marko\\Documents\\Obsidian Vault` → `C:\\Users\\marko\\OneDrive\\Belgeler\\Obsidian Vault`
  - POSIX `$HOME/Documents/...` → Windows tam yol
  Arama: `search_files(pattern="Documents/Obsidian", target="content", path=".../skills")`
- Yeni Hermes özelliği varsa (config.yaml'dan tara) → skill ekle
- Dönüştürülen her Obsidian notu için orijinal dosyayı **koru** (silme — referans olarak kalabilir)
- Yeni skill'in `related_skills` alanında eski ilgili skill'lere bağlantı ekle

### 5. Boylamsal Referans Bağlantıları Kur
- Yeni oluşturulan skill'lerin `related_skills` alanını doldur: alakalı mevcut skill'lere backlink ekle
- Mevcut skill'lerin frontmatter'ını güncelle (ilgili yeni skill'lere backlink)
- Özellikle `dolphin-llama3`, `hibrit-ai-mimarisi`, `hibrit-ai-yonlendirme-kurali` arasında çapraz bağlantı kur

### 5b. Profil Güncelleme Kuralı (KRİTİK)
- User profile güncellemelerinde `memory(action='replace', target='user')` KULLANMA.
- Bunun yerine `memory(action='add', target='user')` ile APPEND yap + tarih damgası ekle.
- Eski entry'ler silinmesin, yeni gözlemler üstüne EKLENSİN.
- Format: `[2026-06-15] Gözlem: ...`
- Böylece tek günün etkileşimi tüm profili ezemez, geçmiş korunur.

### 6. Sync Script'i Çalıştır ve Doğrula
```bash
cd /c/Users/marko/hermes-ai
"C:/Users/marko/hermes-ai/venv/Scripts/python.exe" \
  "C:/Users/marko/AppData/Local/hermes/hooks/sync_skills_to_obsidian.py"
```
- İlk sefer: normal mod (sadece değişenleri yazar)
- İkinci sefer: `--force` flag ile tümünü yeniden yaz
- Çıktıda `[UYARI] Standalone .md bulundu` varsa — dönüştürülmemiş başıboş dosya var demektir, onları da dönüştür

### 7. Obsidian'da Doğrula
- MCP filesystem ile `Obsidian Vault\Hermes\Skills\` altında yeni dosyaları kontrol et
- Obsidian notları (`Hibrit AI Mimarisi.md` gibi orijinal ham notlar) hala duruyor mu kontrol et — dokunma
- Kategori alt dizinlerine (`mlops/`, `autonomous-ai-agents/` vs.) yeni skill'lerin geldiğini doğrula

### 8. Rapor
- Tüm işlemleri özetle
- Raporu doğrudan son yanıt olarak ver (send_message kullanma — cron job modunda otomatik teslim edilir)
- Hiçbir şey değişmemişse: `[SILENT]` yanıtı ver (bildirim gönderilmez)

## Kısıtlar
- Mevcut çalışan skill'leri silme
- Obsidian'daki kişisel notlara dokunma
- Sadece `Hermes\Skills\` klasörüne yaz
- `rm` komutu approval gerekir → bunun yerine `mv <dosya> <dosya>.obsolete` kullan
- MCP filesystem sadece `Obsidian Vault\Hermes` altında çalışır — tam vault'a erişemez

## Pitfall'lar
- **Category with slash:** `mlops/inference` → hata alırsın. Tek düzey kullan: `mlops`
- **Ambiguous skill name:** Root'ta `.md` + kategoride `SKILL.md` varsa ikisi de aynı isimle çarpışır. Önce collision'u çöz
- **env_watcher.py:** .env değişikliklerinden sonra çalıştırmazsan Obsidian'daki env yansıması güncel kalmaz
- **Orijinal notları koru:** Obsidian notlarını silme — kullanıcı kendi el yazısı notlarına değer veriyor
- **Force sync uzun sürer:** 140 skill ~30 saniye alır, timeout'u 120s yap
- **Sync script update:** Sync script sadece `rglob("SKILL.md")` ile çalışır. Root'taki standalone `.md`'leri görmez. Eğer yeni bir standalone varsa önce proper skill'e dönüştür
- **`skill_manage delete` + `absorbed_into` sınırı:** Kaynak ve hedef aynı isimdeyse başarısız olur. MCP filesystem move ile geçici çözüm: `__cleanup_deprecated_<adi>` dizinine taşı, SKILL.md'i `.deprecated` yap
- **Index güncellemesi gerekli:** Dosya sistemi taşıma `skills_list` index'ini güncellemez. Agent restart'ı veya `/reload-skills` komutu gerekir

## Verification Checklist
- [ ] Obsidian vault erişilebilir (`C:\Users\marko\OneDrive\Belgeler\Obsidian Vault`)
- [ ] Tüm skill root `.md` dosyaları incelendi (varsa .obsolete yapıldı)
- [ ] Yeni skill'ler oluşturuldu ve `related_skills` bağlantıları kuruldu
- [ ] Sync script çalıştırıldı (önce normal, sonra --force)
- [ ] Obsidian'da `mlops/`, `autonomous-ai-agents/` altında yeni skill'ler görünüyor
- [ ] İsim çakışması yok (skill_view tüm skill'ler için hata vermeden çalışıyor)
- [ ] Sync script `[UYARI]` vermiyor
