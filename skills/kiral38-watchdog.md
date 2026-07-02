---
name: kiral38-watchdog
category: devops
description: Kiral38 gateway 409 Conflict otomatik yönetimi + multi-profil proaktif bakim
triggers:
  - "409 Conflict"
  - "gateway çöktü"
  - "bot yanıt vermiyor"
  - "polling hatası"
  - "watchdog"
  - "otonom restart"
  - "çift instance"
  - "proaktif bakim"
  - "config drift"
  - "botlar farkli cevap veriyor"
  - "multiprofil esitleme"
---

# Gateway Watchdog + Proaktif Bakim

## Trigger
Telegram bot gateway'lerinde:
- 409 Conflict (çift polling)
- Gateway çökmesi / session timeout
- Botların aynı soruya farklı cevap vermesi
- Config drift (profil farklılıkları)
- "proaktif öneri" / "otonom bakım" talebi
- "öneri sun" / "nereler eksik" / "yapılması gerekenler"

## Anahtar Prensip: PROAKTİF OL — Önce Sun, Sonra Uygula

⚠️ **KRİTİK**: Kullanıcı "öneri sun" dediğinde veya bir sorun bildirdiğinde:
1. **ÖNCE** tüm profilleri tara (sub-agent ile kapsamlı tarama)
2. **ÖNCE** tüm olası iyileştirmeleri numaralı liste olarak SUN
3. Kullanıcı hangilerini istediğini seçer (numara ile)
4. **SONRA** uygula

**Sakın** doğrudan uygulamaya geçme. Kullanıcı "sen neden sunmadın" diye sorar ve ReYMeN bot'uyla karşılaştırır.

Kullanıcı bir sorun bildirdiğinde sadece o sorunu çözme. Hemen:
1. Diğer profillerde de aynı sorun var mı kontrol et
2. Kök nedenleri bul (sadece semptom değil)
3. Tüm profilleri eşitle
4. Cron/otonom çözüm kur ki bir daha yaşanmasın
5. **Öneri sun, kullanıcı söylemeden yap**

⚠️ **PITFALL**: Kullanıcı "öneri sun" dediğinde önce düşünüp tüm olası iyileştirmeleri sırala, sonra uygula. Eksik öneri sunmak = güven kaybı. ReYMeN bot'undan geri kalmamalısın.

## İki Seviyeli Sistem

### Seviye 1: Acil Müdahale (watchdog)
`kiral38_watchdog.py` — her 5dk, no_agent=True
- Son 30dk 409 Conflict sayısı (eşik=10)
- Lock temizle + gateway restart
- Sessiz (sadece müdahale varsa rapor)

### Seviye 2: Proaktif Bakım (umbrella)
`proaktif_bakim.py` — her 30dk, no_agent=True
8 önlem tek scriptte:

| # | Önlem | Ne yapar |
|---|-------|----------|
| 1 | Config drift dedektörü | 3 config.yaml kritik alanlarını karşılaştırır |
| 2 | Gateway watchdog (3 profil) | default/reymen/kiral38 409+çökme koruması |
| 3 | SOUL.md master sync | Master SOUL.md'yi 3 profile otomatik kopyalar |
| 4 | state.db prune (30 gün) | Eski session'ları temizler |
| 5 | MEMORY.md sync | 3 profil arasında memory eşitler |
| 6 | Haftalık rapor (Pazar) | 3 bot durum özeti |
| 7 | Config template kontrol | Gerekli alanlar var mı diye doğrular |
| 8 | Gateway health | PID/state/uptime kontrol |

## Çoklu Profil Sorun Giderme Kontrol Listesi

Botlar aynı soruya farklı cevap veriyorsa şunları kontrol et:

- [ ] SOUL.md aynı mı? (master kopya ile sync)
- [ ] MEMORY.md var mı ve aynı mı? (hepsine ekle/sync)
- [ ] USER.md var mı?
- [ ] shared_memories symlink'i var mı? (junction point)
- [ ] config.yaml: external_dirs aynı mı?
- [ ] config.yaml: display.skin aynı mı?
- [ ] config.yaml: approvals.mode aynı mı?
- [ ] config.yaml: model/provider aynı mı?
- [ ] state.db boyutları (0KB = hiç çalışmamış, normal)
- [ ] Gateway PID'leri yaşıyor mu? (çift instance var mı?)
- [ ] Startup VBS/BAT güncel mi? (AppLocker bypass)
- [ ] durum.json güncel mi?

## Dosyalar
- `~/AppData/Local/hermes/scripts/kiral38_watchdog.py` — acil watchdog
- `~/AppData/Local/hermes/scripts/proaktif_bakim.py` — 8 önlem
- `~/AppData/Local/hermes/profiles/*/watchdog_counter.json` — sayaç
- `reymen/scripts/start_botlar.vbs` + `.bat` — startup script'leri
- `.ReYMeN/decisions.md` — karar kaydı

## Büyük Modül Geliştirme (Eksik Kapatma) Pattern

Kullanıcı "7 eksik kapat" / "hepsini yap" / eksik listesini verdiğinde 4+ modül paralel geliştirme:

### Aşama 1: Grupla ve Önceliklendir
Eksikleri 3'erli gruplara ayır (max_concurrent_children=3). Her grup için:
- Bağımsız modül mü? (farklı dosyalara yazılır)
- Ortak bağımlılığı var mı? (aynı config/beyin API'sı)
- Tahmini süre?

### Aşama 2: Sub-agent'lara Dağıt
```python
delegate_task(tasks=[
    {"goal": "Modül 1", "context": "proje yapısı, API referansı", "toolsets": ["file","search"]},
    {"goal": "Modül 2", ...},
    {"goal": "Modül 3", ...},
])
```
Her sub-agent'a **tam context** ver: mevcut kod yapısı, dosya adları, pattern, API örnekleri.

### Aşama 3: Sub-agent Bittiğinde Yapılması Gerekenler
1. **Dosyaları fiziksel kontrol et** — `ls -la` ile her dosyanın varlığını doğrula
2. **Syntax kontrol** — `python -c "ast.parse(open(...).read())"`
3. **Import kontrol** — `python -c "from reymen.x import y"`
4. **Eksik dosya varsa elle ekle** — sub-agent bazen write_file yapmayı unutur
5. **Git add + commit** — her batch sonrası

### Aşama 4: Kalanı İkinci Batch'e Bırak
İlk 3 modül tamamlanınca kalanları ikinci delegate_task'e ver.

### Pitfall: Sub-agent Dosya Yazmayı Unutabilir
Sub-agent raporunda "write successful" yazar ama `git status`'te dosya görünmez. Bunun sebepleri:
- Sub-agent write_file timeout almış ama raporlamamış
- Dosya yanlış yola yazılmış
- Git staging'de görünmüyor (belki zaten izleniyor)

**Çözüm:** Her sub-agent batch'i sonrası:
```bash
git status --short     # staging'deki dosyalar
ls -la <beklenen_dosya>  # fiziksel dosya
git ls-files --stage <dosya>  # git'te izleniyor mu?
```

## GitHub Public Readiness Checklist

Private → Public yapmadan önce kontrol edilecekler:

### 🔴 KRİTİK (olmazsa public YAPMA)
- [ ] **PAT token sızıntısı** — `git remote -v`'de ghp_... var mı? → `git remote set-url origin`
- [ ] **.env dosyası** — git'te izlenmiyor mu? (`git check-ignore .env`)
- [ ] **API key hardcode** — kod içinde `sk-...` veya `ghp_...` var mı? (`grep -rn 'sk-\|ghp_\|api_key'`)
- [ ] **.db dosyaları** — .gitignore'da ve git'te takip edilmiyor mu?
- [ ] **state.db** — git LFS'e alınmış veya .gitignore'da mı?

### 🟠 ÖNEMLİ
- [ ] **LICENSE** dosyası var mı? (genelde MIT)
- [ ] **README.md** güncel mi? (kurulum, kullanım, screenshot)
- [ ] **CONTRIBUTING.md** var mı?
- [ ] **CHANGELOG.md** sürüm notları güncel mi?
- [ ] **pyproject.toml** versiyon + URL + classifiers doğru mu?
- [ ] **GitHub topic** etiketleri eklendi mi? (ai, agent, cli, turkce)
- [ ] **CODE_OF_CONDUCT.md** var mı?
- [ ] **SECURITY.md** (güvenlik raporlama) var mı?

### 🟡 İYİLEŞTİRME
- [ ] **ISSUE_TEMPLATE** + **PULL_REQUEST_TEMPLATE** hazır mı?
- [ ] **CI pipeline** yeşil mi? (GitHub Actions)
- [ ] **Test coverage** en az %30?
- [ ] **Dokümantasyon** (docs/) temel sayfaları içeriyor mu?
- [ ] **.github/FUNDING.yml** var mı? (bağış/bağlantı)
- [ ] **README.md**'de star/badge görünür mü? (CI, Python version, license)
- [ ] **Proje tanıtım yazısı** hazır mı? (LinkedIn/Twitter/Telegram için)

### 🔵 Public Yaptıktan Sonra
- [ ] **GitHub Pages** aktif et (docs/)
- [ ] **PyPI publish** (pip install ile kurulabilir)
- [ ] **HackerNews/Reddit** tanıtımı
- [ ] **İlk issue** gelince cevaplamaya hazır ol

## Git History Security Scan (Public Öncesi)

Private → Public yapmadan ÖNCE git history'de sızan secret kalmadığından emin ol.

### Hızlı Tarama Komutları

```bash
# .env hiç commit'lenmiş mi?
git log --all --diff-filter=A -- .env

# API key pattern'leri (sk-, ghp_, xoxp-, AIza)
git log --all --pickaxe-regex -S 'sk-[A-Za-z0-9]{20,}' --source -- .
git log --all --pickaxe-regex -S 'ghp_[A-Za-z0-9]{36}' --source -- .

# Bot token'ları (sayı:harf-karma)
git log --all --pickaxe-regex -S '[0-9]{8,10}:[A-Za-z0-9_-]{35}' --source -- .

# IP adresleri
git log --all --pickaxe-regex -S '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' --source -- .

# Özel anahtarlar (PRIVATE KEY, BEGIN RSA, BEGIN OPENSSH)
git log --all --pickaxe-regex -S 'BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY' --source -- .
```

### BFG Repo-Cleaner ile Temizlik

History'de secret bulunursa:

```bash
# İndir + çalıştır
curl -L -o bfg.jar https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar
java -jar bfg.jar --replace-text <(echo 'sk-xxx...') repo.git

# GC ile temizle + force push
cd repo.git && git reflog expire --expire=now --all && git gc --prune=now --aggressive
git push --force --all && git push --force --tags
```

### Ne Zaman BFG Gerekli?

| Durum | BFG? | Alternatif |
|-------|:----:|------------|
| .env diskte ama git'te HİÇ commit'lenmemiş | ❌ | `.gitignore` kontrol et |
| .env eski commit'te var, yeni .gitignore'da | ✅ | BFG ile history'den sil |
| API key kod içinde hardcode | ✅ | BFG + yeni commit |
| API key test dosyasında (fake) | ❌ | Açıklama ekle |
| Bot token git'te | ✅ | BFG + token revoke |
| Bot token diskte ama gitignore'da | ❌ | Script'i sil + token revoke |

### Bu Projede Bulunanlar

- `.env` → ✅ Hiç commit'lenmemiş
- `sk-` API key'leri → ✅ Gerçek key yok
- `ghp_` GitHub token → ✅ Sadece test fake'leri
- Bot token → ⚠️ Diskte `ReYMeN-memory-backup/` içinde var ama `.gitignore`'da
- Özel anahtarlar → ✅ Sadece test kodlarında fake

**Aksiyon:** Diskteki token'lı script'leri sil + token'ı BotFather'dan revoke et.

## Multi-Modül Sub-Agent Geliştirme Pitfall'ları

| Pitfall | Belirti | Çözüm |
|---------|---------|-------|
| **Sub-agent write_file başarısız** | "file created" der ama git status'ta yok | Dosyayı `ls -la` ile kontrol et, yoksa elle yaz |
| **Case-insensitive FS tuzağı** | Cline `ReYMeN/` klasörüne yazar, aslında `reymen/` içine gider | `os.path.samefile('ReYMeN','reymen')` ile kontrol |
| **Ortak config değişikliği** | Sub-agent'lar pyproject.toml'ı bozabilir | Her batch'ten sonra `python -c "compile()"` ile pyproject.toml doğrula |
| **Sub-agent timeout** | 3+ dk süren işlemlerde sub-agent yarıda kesilir | Süreyi kısalt (her modül max 500 satır) |
| **Sub-agent eski context kullanır** | Sub-agent'ın gönderdiği context'te yanlış dosya yolu olabilir | Context'te HER ZAMAN tam proje yolu ver |
| **Git push rejected** | "cannot lock ref" — remote değişmiş | `git pull --rebase && git push` |

## Cron Job'lar
| Job | Schedule | Mod |
|-----|----------|-----|
| proaktif-bakim | 30dk | no_agent — sessiz, müdahale varsa rapor |
| kiral38-watchdog | 5dk | no_agent — 409 eşiği aşarsa rapor |

## Pitfall'lar

1. **Çift instance** — Aynı profilden 2 gateway process'i 409 Conflict'e yol açar. Watchdog otomatik temizler.
2. **AppLocker** — `~/.local/bin/hermes.exe` bloklanır. `venv/Scripts/hermes.exe` kullan.
3. **state.db boyutu** — 0KB = bot hiç çalışmamış. Normal, müdahale gerekmez.
4. **Proxy/Scheduled Task** — Windows Scheduled Task ile gateway başlatma AppLocker'dan etkilenebilir. Python subprocess ile başlat daha güvenilir.
5. **MEMORY.md kaybı** — Profil .env güncellemesi sırasında TELEGRAM_BOT_TOKEN kaybolabilir. Hex byte encoding ile yaz.
6. **SOUL.md cache** — `_dosya_oku()` @lru_cache kullanır. Değişiklik sonrası gateway restart gerek.
7. **Proaktif ol** — Kullanıcı bir sorun bildirdiğinde sadece o sorunu değil, diğer profillerdeki benzer sorunları da tespit edip çöz. "Öneri sun" denmeden önce sun.
8. **PAT token sızıntısı** — `git remote -v` ile remote URL'de ghp_... token'ı var mı kontrol et. Varsa hemen `git remote set-url origin` ile temizle. Detay: `references/2026-07-01-pat-token-sizintisi.md`
9. **Paralel modül geliştirme** — 3+ yeni modül aynı anda geliştirilecekse, her birini ayrı sub-agent'a ver (delegate_task tasks=[]). Her sub-agent aynı bağlamı (config yapısı, Beyin API'sı) almalı. Detay: `references/2026-07-01-3-yeni-modul-pattern.md`

## Proaktif Öneri Şablonu (Kullanıcıya Sunulacak)

Kullanıcı "öneri sun" dediğinde şu kategorileri tara:

### 🔧 Config & Hizala
- shared_memories symlink'i var mı? (tüm profillerde)
- Config yedek/eski dosyalar var mı? (temizle)
- startup VBS/BAT güncel mi? (AppLocker bypass)
- durum.json güncel mi?

### ⚡ Performans & Sağlık
- state.db prune gerekli mi? (30 gün)
- Gateway health (PID/state/uptime)
- Çift instance var mı?

### 🛡️ Kalıcı Çözüm
- Otonom watchdog script'i ekle
- Cron job kur
- GitHub push
- Projeye startup script'lerini ekle

## Tam Workflow: Tarama → Sunma → Uygulama → Push

Kullanıcı "proaktif öneri" / "tara" / "eksikler" dediğinde veya bir sorun bildirdiğinde kullanılacak 4 aşamalı workflow:

### Aşama 1: Kapsamlı Tara (sub-agent ile)
```python
delegate_task(
    goal="ReYMeN-Ajan projesini tara ve proaktif öneriler çıkar",
    context="Proje yapısı, config, test, güvenlik, GitHub, dokümantasyon",
    toolsets=["terminal", "file", "search"]
)
```
Sub-agent tüm projeyi tarar, 20-30 öneri çıkarır. Her öneriye öncelik seviyesi verir (🔴KRITIK/🟠ONEMLI/🟡IYILESTIRME/🔵NICEL).

### Aşama 2: Listele ve Sun
Önerileri öncelik sırasına göre numaralı tablo olarak sun. Kullanıcı hangi numaraları istediğini söyler (örn. "20,21,22,23,24,25,26,27,28,29,30").

**FORMA**: 
```
| # | Öneri | Ne / Nerede / Neden | Çözüm |
```

### Aşama 3: Batch Uygula (todo ile)
```python
todo(todos=[
    {"id":"20","content":"...","status":"in_progress"},
    ...
])
```
Sırayla uygula. Her öneri:
- Dosya oku (gerekirse)
- patch/write_file ile düzelt
- compile/import ile doğrula
- todo'da completed işaretle

### Aşama 4: GitHub Push (kalıcı kayıt)
```bash
git add -A && git commit -m "[özet]" && git push
```
decisions.md'ye kaydet. Böylece projeyi indiren kişi aynı sorunları yaşamaz.

### Önemli Pitfall'lar

1. **Sub-agent'ın 30 önerisi + benim önerilerim çelişebilir** — sub-agent daha kapsamlı tarar. Onun sonuçlarını kullan.
2. **PAT token sızıntısı** — remote URL'de düz metin token varsa hemen temizle: `git remote set-url origin https://github.com/...`
3. **Birleştirilmiş öneriler** — 28 ve 30 (ZIP + disk) aynı olabilir. Tekrarları birleştir.
4. **Her değişiklik sonrası syntax/import doğrula** — özellikle pyproject.toml, YAML, TOML dosyalarında
5. **Versiyon tutarsızlığı** — CHANGELOG vs pyproject.toml versiyonlarını her zaman eşitle
