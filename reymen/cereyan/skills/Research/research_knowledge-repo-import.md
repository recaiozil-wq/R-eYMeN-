---
name: knowledge-repo-import
description: GitHub repo'yu klonla, içerik dizinini çıkar, Hermes skill + Obsidian vault kopyasını otomatik oluştur.
title: "Knowledge Repo Import"
tags: [github, clone, obsidian, knowledge-base, import, research]
category: research
audience: user
---


> **Kategori:** research

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | GitHub repo'yu klonla, içerik dizinini çıkar, Hermes skill + Obsidian vault kopyasını otomatik oluştur. |
| **Nerede?** | research/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Knowledge Repo Import

## Trigger
Kullanıcı bir GitHub repo URL'si paylaşır ve "kaydet", "not defterine ekle", "skill yap", "bize yarar mı", "güvenlik kontrol" gibi bir istekle birlikte gelirse.

## MOD 0: Repo Değerlendirme + Güvenlik Kontrolü (ÖNCE)
Repodan skill/prompt yüklemeden önce şu adımlar ZORUNLU:

1. **Repo bilgisi al** - README.md, repo yapısı, lisans, star sayısı
2. **Güvenlik taraması:**
   - Script'lerde `eval()` / `exec()` / `os.system()` var mı?
   - `curl`/`wget`/`requests` ile external network çağrısı var mı?
   - Gömülü token/şifre var mı?
   - `requirements.txt`'de şüpheli paket var mı?
   - Upstream ile fork arasında SHA farkı var mı? (önemli script'leri karşılaştır)
3. **Fayda analizi:**
   - Kaç skill/prompt içeriyor? (phases/**/outputs/*.md)
   - Hangi konuları kapsıyor? Hermes'te eksik olan ne var?
   - Skill formatı Hermes ile uyumlu mu? (SKILL.md frontmatter)
4. **Rapor formatı:**
   - Güvenlik: TEMİZ / RİSK var
   - Fayda puanı: X/10
   - Öne çıkan konular
   - "Kurmak istiyor musun?" ile sonlandır

## Skill/Prompt Kurulumu (Phases/Outputs Yapısı)

Repodaki skill'ler `phases/**/outputs/skill-*.md` yapısındaysa (AI Engineering from Scratch tarzı):

**DOĞRU YÖNTEM:** Repoyu klonla, kendi `install_skills.py` scriptini kullan:
```
git clone --depth 1 <url>
cd <repo>
python3 scripts/install_skills.py "<HERMES_SKILLS_DIR>" --type all --force
```

**YANLIŞ YÖNTEM (KULLANMA):** `npx skills add <repo>` — bu sadece repo kökündeki `.claude/skills/` dizinini tarar. `phases/**/outputs/` altındaki skill'leri bulamaz. AI Engineering from Scratch tipi repolarda 2 skill bulur (gerçekte 487 varken).

**Ek adımlar:**
- `.claude/skills/` altındaki skill'leri de manuel kopyala (varsa)
- `manifest.json`'ı kontrol et: kaç adet yüklendi?
- `sync_skills_to_obsidian.py` çalıştır
- Obsidian'a repo notu oluştur (içerik, hangi skill'ler, kurulum tarihi)

### Windows Defender Uyarısı (Güvenlik Repoları)
Pentest/güvenlik skill repolarında (kali-pentest gibi) `netcat.md`, `payloads.md`, `reverse_shell.md` gibi dosyalar Windows Defender tarafından trojan olarak algılanabilir:
- `Trojan:PowerShell/ReverseShell.HNAA!MTB` — netcat örnekleri
- `Backdoor:PHP/Remoteshell.F` — web shell örnekleri
- `Trojan:Win32/LummaStealerClick.S!MTB` — click hijack örnekleri

**Kural:** Güvenlik skill'i yüklerken:
1. Kurulumdan SONRA Windows Defender threat listesini kontrol et: `Get-MpThreatDetection`
2. Flaglenen dosyaları skill'den kaldır (genellikle eğitim amaçlı örnek kodlar)
3. Windows Defender hızlı tarama çalıştır: `MpCmdRun.exe -Scan -ScanType 1`
4. Threat'leri temizlet (CMDLine detection'ları geçmiş komut kayıtlarıdır, silinemez)
5. Kullanıcıya raporla: hangi dosyalar silindi, hangileri false positive

**Alternatif:** Eğer skill'in orijinal dosyası Windows'ta bozuksa (Errno 22 - Invalid argument), git clone sırasında hasar görmüş olabilir. Python ile `shutil.copy2` yerine try/except ile tek tek kopyala, hatalı dosyaları atla.

### Skill vs Sistem Değişikliği Ayrımı
Kullanıcı tercihi: **SADECE skill istiyor, sistem değişikliği değil.**

Repoları değerlendirirken:
- **Skill-only:** Sadece SKILL.md/prompt dosyaları kopyalanır. Hermes'in mevcut yapılandırması değişmez. ✅ Güvenli
- **System-changing:** pip paketi kurulumu, memory provider değişikliği, config.yaml güncellemesi, daemon/cron kurulumu gerektirir. ❌ Kullanıcı istemiyor

Örnekler:
- `kali-pentest` → skill-only ✅
- `ai-engineering-from-scratch-zh` → skill-only ✅
- `mnemosyne` → memory provider değişikliği, pip install, mevcut MEMORY.md/USER.md kapatma ❌
- `brigade` → pipx install, cron/daemon, Hermes'in kendi memory sistemiyle çakışma ❌

Raporda mutlaka belirt: "Bu repo skill-only mi yoksa system-changing mi?"

## MOD 3: Mevcut Hermes Skill'leri ile Repo Karşılaştırması

Repodaki skill'leri yüklemeden ÖNCE mevcut Hermes kütüphanesini kontrol et:

### Adım 1 — skills_list() ile mevcut durumu tara
```python
# Önce skills_list() çalıştır, repo'daki skill adlarını mevcutlarla karşılaştır
# Varsa → güncelleme gerekip gerekmediğini belirle
# Yoksa → yeni skill oluştur
```

### Adım 2 — Boyut karşılaştırması YETERLİ DEĞİL, içerik analizi yap
```python
# Repo'daki SKILL.md === büyük şişkin dosya (eski format)
# Hermes'teki SKILL.md === küçük Router (3-4KB) + references/ dosyaları
#
# Eğer repo > Hermes ise:
#   İhtimal A: Repo güncel, Hermes eski → references/ ekle
#   İhtimal B: Repo ESKİ/şişkin, Hermes Router+Reference'a bölünmüş → güncelleme GEREKMEZ
#
# Karar: skill_view() ile Hermes versiyonunun references/ yapısını kontrol et
# Eğer references/ varsa → Router+Reference yapısı oturmuş, repo eski demektir
```

### Adım 3 — Güncelleme stratejisi
```python
# Repo versiyonu büyük AMA Hermes'te references/ varsa:
#   → Repo ESKİ şişkin versiyon. Güncelleme gerekmez.
#   → Kullanıcıya raporla: "Repo versiyonu şişkin/eski, Hermes zaten güncel"
#
# Repo versiyonu farklı içerik İÇERİYORSA (Hermes'te olmayan konular):
#   → Yeni references/ dosyası oluştur (skill_manage write_file ile)
#   → SKILL.md'ye bir satır yönlendirme ekle
#   → TÜM repodaki içeriği SKILL.md'ye kopyalama (şişkinlik yasağı!)
#
# Repo versiyonu GERÇEKTEN daha güncelse (Hermes references/'siz):
#   → skill_manage edit ile SKILL.md'yi güncelle
```

### Pitfall
- `npx skills add` repo kökündeki `.claude/skills/` dizinini tarar — eğer skill'ler `phases/` içinde gömülüyse BULAMAZ
- `--type all` ile hem skill hem prompt hem agent dosyaları yüklenir
- `--force` ile çakışmaları otomatik aş (çakışma varsa uyarı basar, ilkini korur)
- Repo büyükse (2000+ dosya) `--depth 1` ile clone'la
- **Repo versiyonu büyük diye güncel sanma** — Hermes Router+Reference yapısına bölmüş olabilir. Önce `skill_view()` ile references/ varlığını kontrol et.
- **"Hepsi yüklü" raporu yeterli değil** — Kullanıcı "yükle" dediyse, zaten varsa bile raporla ve fark varsa güncelle. Boş rapor kullanıcıyı tatmin etmez.

## MOD 1: Skill + Vault Copy (varsayılan)
1. Repoyu `C:\\Users\\marko\\Desktop\\` altına klonla: `git clone <url>`
2. Kök dosyaları tara: `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md` vb.
3. Eğer `README.md` varsa:
   - TOC/başlıkları çıkar (madde işaretli satırları veya numbered sections).
   - Skill dosyasını `C:\\Users\\marko\\AppData\\Local\\hermes\\skills\\research\\` altına `<repo-ismi>.md` olarak yaz.
   - Obsidian vault'a:
     - `C:\\Users\\marko\\OneDrive\\Belgeler\\Obsidian Vault\\<RepoName>\\README.md`
     - `C:\\Users\\marko\\OneDrive\\Belgeler\\Obsidian Vault\\<RepoName>.md`
     klasör ve kasa notu olarak kopyala.
4. Eğer `README.md` yoksa:
   - Klasör yapısını ve dosya adlarını skill içine al.
   - Obsidian'a sadece kasa notu olarak kaydet.

## MOD 2: Direkt Vault Clone + MOC (repo .md formatındaysa)
Repo içindeki dosyalar zaten `.md` (Markdown) formatındaysa ve doğrudan Obsidian'da okunabilir durumdaysa:

1. **Klonla:** `cd "<VAULT_YOLU>" && git clone <url>`
2. **Klasör adını değiştir:** `mv <repo-adı> "<Anlamlı Klasör Adı>"` (boşluklu, Türkçe isim)
3. **İçeriği tara:** `.md` dosyalarını listele, ana başlıkları çıkar
4. **MOC (Map of Content) oluştur:** `000_<KlasörAdı>_Giris.md` adında bir dosya yaz:
   - Klasör yapısını tablo olarak göster
   - Her .md dosyasına `[[DosyaAdı]]` wikilink'i ile bağlantı ver
   - Ana başlıkları grupla
   - GitHub repo linkini not olarak ekle

### MOC Şablonu
```markdown
# 🗺️ <Klasör Adı> — Ana Menü

> <kısa açıklama>

## 📂 Klasör Yapısı
```
<klasör>
├── 000_<isim>_Giris.md   ← (bu dosya)
├── <dosya1>.md
└── <altklasör>/
    └── <dosya2>.md
```

## 🔗 Hızlı Bağlantılar
| Başlık | Dosya | Açıklama |
|--------|-------|----------|
| 📄 **<başlık>** | [[<dosya>]] | <açıklama> |

## 📌 Not
> [[<owner/repo>|GitHub reposu]] üzerinden klonlanmıştır.
> Güncellemeler için `git pull` yapabilirsin.
```

### Pitfall
- Klasör adında `&` gibi özel karakterler varsa terminal komutlarında tırnak içine al: `"Siber Güvenlik & Yazılım SSS"`
- `git clone` doğrudan vault içine yapılır, sonra `.git` klasörü kalır — bu Obsidian için sorun değildir
- MOC dosyasını `000_` ile adlandır (Obsidian'da üstte görünür)

## Vault Kuralları
- Ana başlıklar kök seviyesinde ayrı klasör olmalı (iç içe gruplama yok).
- Masaüstü tek klasör, içinde `handbooks/` gibi alt klasörler olabilir.

## Kullanıcı Tercihleri
- Kullanıcı "neden bunu yapıyorsun" gibi açıklama istemez, sonucu raporla.
- Her adımda onay bekleme, otonom ilerle.
- Skill + Obsidian kopyasını tek seferde yap, raporla.

## Çıktı Formatı
```
DONE
Kaydedildi:
- Skill: <skill_yolu>
- Obsidian klasör: <klasör_yolu>
- Obsidian kasa notu: <kasa_not_yolu>
```

## Pitfalls
- Repo çok büyükse tüm dosyaları değil, kök README + ilk seviye dosya listesi yeterli.
- Git clone hatalıysa (network, path) tekrar dene; başarısız olursa kullanıcıya bildir.
- Obsidian vault yolu her zaman `C:\\Users\\marko\\OneDrive\\Belgeler\\Obsidian Vault` olmalı; `Documents` altındaki yanlış yolu kullanma.
- Skill yüklerken `npx skills add` kullanma — phases/ altındaki skill'leri bulamaz. Reponun kendi `install_skills.py` scriptini kullan.
- `install_skills.py` çalışmazsa (yoksa veya hatalıysa) skill'leri manuel kopyala:
  ```
  find phases -name "*.md" -path "*/outputs/*" | while read f; do
    name=$(basename "$f" .md)
    mkdir -p "<HERMES_SKILLS>/$name"
    cp "$f" "<HERMES_SKILLS>/$name/SKILL.md"
  done
  ```
- `.claude/skills/` altındaki skill'ler ayrıca kopyalanmalıdır (install_skills.py onları görmez).
