---
name: fork-project-audit
description: >-
  Analyze a forked/modified codebase to identify original files vs copied files,
  broken import chains, code volume by origin, and produce structured delegation
  briefs for Claude Code.
---


> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | >- |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Fork Project Audit

Bir proje fork'landığında veya kopyalandığında, hangi dosyaların **yeni/özgün**,
hangilerinin **kopya** olduğunu bulmak için sistematik yöntem.

## Ne Zaman Kullanılır

- Bir proje başka bir projeden fork'lanmış/kopyalanmışsa
- "Bu kodun ne kadarı bize ait?" sorusu sorulduğunda
- Projeyi Claude Code'a devredeceksen ve hangi dosyalara dokunacağını belirlemen gerekiyorsa
- Testlerin neden çalışmadığını anlamak için import bağımlılıklarını kontrol ederken

## Adımlar

### 0. Lisans Uyumluluğu Kontrolü (ÖNCE)

Bir projeyi fork'lamadan/kopyalamadan önce **orijinal lisansı kontrol et** ve koru. Bu adım atlanırsa telif hakkı ihlali oluşabilir.

#### 0.1 Orijinal Lisansı Bul

```bash
# Orijinal projenin LICENSE dosyasını oku
gh repo view <org>/<repo> --json licenseInfo 2>/dev/null
# veya manuel:
curl -s https://raw.githubusercontent.com/<org>/<repo>/main/LICENSE | head -5
```

#### 0.2 Lisans Tipine Göre Yükümlülükler

| Lisans | Copyright koru? | Lisans metnini koru? | Başka? |
|--------|----------------|---------------------|--------|
| MIT | ✅ Zorunlu | ✅ Zorunlu | Yok |
| Apache 2.0 | ✅ Zorunlu | ✅ Zorunlu | NOTICE dosyası varsa onu da koru |
| GPL | ✅ Zorunlu | ✅ Zorunlu | Aynı lisansla yayımla |
| Unlicense/CC0 | Gerekmez | Gerekmez | İsteğe bağlı |

#### 0.3 Fork'ta LICENSE Dosyasını Doğrula

```bash
# Fork'taki LICENSE ile orijinali karşılaştır
diff <(curl -s https://raw.githubusercontent.com/<org>/<repo>/main/LICENSE) LICENSE
```

**Kritik kontroller:**
- [ ] Orijinal copyright bildirimi korunmuş mu? (`Copyright (c) YYYY <Sahip>`)
- [ ] Orijinal lisans metninin tamamı duruyor mu?
- [ ] Kendi adını copyright satırına **eklemedin** (orijinali silip kendini yazmadın)?
- [ ] Varsa NOTICE dosyası taşınmış mı?
- [ ] Lisans metnine ek kısıtlama/şart eklenmemiş mi?

**Doğru yaklaşım:** Orijinal LICENSE dosyası aynen kopyalanır. Kendi teşekkür/atıf notların lisans metninin ALTINA veya ayrı bir ACKNOWLEDGMENTS.md dosyasına eklenir.

```license
MIT License

Copyright (c) 2025 Orijinal Yazar    ← korunur

Permission is hereby granted...
[lisans metninin tamamı aynen durur]

---                               ← ayraç ile ayrılır
Teşekkürler / Acknowledgments     ← ek notlar
This project is based on...
```

#### Pitfall — Copyright Değiştirme

❌ **YANLIŞ:** `Copyright (c) 2025 Orijinal Yazar` → `Copyright (c) 2026 Kendi Adım`
✅ **DOĞRU:** Orijinal satır aynen kalır. İstersen altına `Copyright (c) 2026 Kendi Adım` ekleyebilirsin (ama zorunlu değil).

MIT lisansı "The above copyright notice shall be included" der. Copyright satırını silmek veya değiştirmek lisans ihlalidir.

### 1. Dosya Sayımı ve Köken Tespiti

```bash
# Toplam .py sayısı (venv/pycache/git hariç)
find "$PROJE" -name "*.py" -not -path "*/venv/*" -not -path "*/__pycache__/*" -not -path "*/.git/*" | wc -l

# Klasör bazında dağılım
cd "$PROJE" && for d in */; do
  count=$(find "$d" -name "*.py" -not -path "*/venv/*" -not -path "*/__pycache__/*" 2>/dev/null | wc -l)
  echo "$count  $d"
done | sort -rn

# Toplam kod satırı
find "$PROJE" -name "*.py" -not -path "*/venv/*" -not -path "*/__pycache__/*" -exec cat {} \; | wc -l

# En büyük dosyalar
find "$PROJE" -name "*.py" -not -path "*/venv/*" -not -path "*/__pycache__/*" -exec wc -l {} \; | sort -rn | head -20
```

### 2. Özgün Dosyaları Tespit Et

```bash
# Fork'a özel isimler ara (ör: proje adı)
grep -rl "Reymen\|reymen\| Rey " *.py 2>/dev/null | head -10

# Fork'a özel dosyaları kontrol et
for f in motor.py yetenek_fabrikasi.py ...; do
  [[ -f "$f" ]] && wc -l "$f"
done
```

### 3. Import Zinciri Analizi

```bash
# Her dosyada Hermes/Orijinal import'larını tara
grep -rn "^from hermes\|^import hermes" tests/ --include="*.py" 2>/dev/null | head -30

# Fork'un kendi import'larını tara
grep -rn "^from motor\|^from sistem\|^from yetenek" tests/ --include="*.py" 2>/dev/null

# Import'u dene — nerede kırıldığını bul
python -c "from hermes_state import SessionDB" 2>&1
# Zinciri takip et: hermes_state.py → agent/memory_manager.py → tools/registry.tool_error
```

### 4. Test Durumu Analizi

```bash
# Toplam test sayısı
find tests/ -name "*.py" | wc -l

# Fork import'lu testler
grep -rl "from motor\|from sistem" tests/ --include="*.py" 2>/dev/null | wc -l

# Orijinal import'lu testler
grep -rl "from hermes\|import hermes" tests/ --include="*.py" 2>/dev/null | wc -l
```

### 5. Kod Miktarı Özeti

```
Orijinal proje (kopya):   XXX dosya, XXX satır
Fork'a özel (yeni):        XX dosya, XXX satır
Oran:                      %X fork, %X kopya
```

### 6. Claude Code Delegasyon Brifi Oluştur

Brife şunları koy:
- **SADECE şu dosyalara dokun** listesi (fork'a özel dosyalar)
- **DOKUNMA** listesi (orijinal projeden kopya dosyalar)
- Kırık import zincirleri (düzeltmeye çalışma uyarısı)
- Çalışan testler ve çalışmayan testler
- Kod standartları (fork'un kendi kuralları)
- Graceful degrade notları

### Brif Formatı (Claude Code'a verilecek)

> **GÖREV: ...**
> **Hedef klasör:** ...
> **SADECE şu XX dosyaya dokun:**
> - dosya1.py — ne iş yapar
> - dosya2.py — ne iş yapar
> **DOKUNMA:** (kopya dosyaların listesi)
> **Test:** sadece şu test çalışır

### 7. Sistematik Modül Testi

Import edilen modüllerin **gerçekten çalıştığını** doğrula. Bir modül import edilebilir ama runtime'da kırılabilir.

Fork reference testlerini düzeltme workflow'u için:
→ `references/hermes-reference-test-fix.md` (genel workflow)
→ `references/hermes-reference-test-fix-17-haziran-2026.md` (spesifik oturum)

```python
# Test script template
moduller = ["modul1", "modul2", "..."]
for mod in moduller:
    try:
        __import__(mod)
        # Runtime test
        try:
            # Modüle göre spesifik test çağrısı
            print(f"  [OK]  {mod}")
        except Exception as e:
            print(f"  [RUNTIME] {mod}: {e}")
    except Exception as e:
        print(f"  [IMPORT]  {mod}: {e}")
```

#### Kategori Sistemi

| Sonuç | Anlamı | Ne yapılmalı |
|-------|--------|-------------|
| `[OK]` | Çalışıyor | Hiçbir şey |
| `[IMPORT]` | Import aşamasında kırık | Zincirdeki eksik modül/fonksiyonu bul |
| `[RUNTIME]` | Import edilir ama çalışmaz | Class adı, path, config hatası olabilir |

#### Runtime Test Stratejisi

```python
# Session DB test
if mod == "session_db":
    from session_db import AdvancedSessionStorage
    import tempfile
    db = AdvancedSessionStorage(str(tempfile.mkdtemp()))
    db.close()

# Provider transport test
if mod == "provider_transport":
    from provider_transport import RuntimeProviderEngine

# Tool registry test
if mod == "tools.registry":
    from tools.registry import registry
    tools = registry.get_definitions()  # Kaç tool kayıtlı?
```

### 8. Tool Sistemi Doğrulama

Tool sisteminin sadece import edilmesi yetmez, **çalıştığını da doğrula**:

```bash
# Registry'de tool var mı?
python -c "from tools.registry import registry; print(len(registry.get_definitions()))"

# Belirli bir tool çalışıyor mu?
python -c "from tools.skill_manager_tool import skill_manage; print(skill_manage('list'))"
```

### 9. Özellik Karşılaştırma Tablosu

Fork ile orijinal arasında sistematik karşılaştırma:

```
| Özellik | Orijinal'de var mı? | Fork'ta var mı? | Çalışıyor mu? |
|---------|---------------------|-----------------|---------------|
| Provider | ✅ | ✅ kopya | ⚠️ test edilmedi |
| Gateway  | ✅ | ✅ kopya | ❌ import zinciri kırık |
| Session  | ✅ | ✅ kopya | ✅ çalışıyor |
```

#### Fork'a Özel Olanları Vurgula

```
**Fork'ta olup orijinalde OLMAYAN:**
- Kapalı öğrenme döngüsü ✅
- Türkçe arayüz ✅
- Planlayıcı ✅

**Orijinalde olup fork'ta OLMAYAN:**
- Gateway sistemi ❌
- Plugin sistemi ❌
```

### 10. Claude Code Devretme Brifi

Analiz bittiğinde şu formatta bir brif hazırla:

> **GÖREV: [ne yapılacak]**
> **Hedef klasör:** [tam yol]
> 
> **SADECE şu XX dosyaya dokun:**
> - dosya1.py — ne iş yapar (XX satır)
> - dosya2.py — ne iş yapar (XX satır)
> 
> **ASLA DOKUNMA:**
> - modul_x/ (kopya, import zinciri kırık)
> - tests/ (orijinal testler, referans)
> 
> **Test:** python -m pytest test_xxx.py -v (çalışan testler)
> 
> **Kod standartları:** [fork'un kuralları]
> 
> **Graceful degrade:** [varsa notlar]

## Pitfalls

- **Shell path boşlukları:** Windows'ta `"Reymen Proje"` gibi boşluklu yollar tırnaklanmalı
- **.py sayısı venv içerebilir:** `-not -path "*/venv/*"` filtresini UNUTMA
- **import testi yanıltabilir:** Bazı modüller import edilir ama çalışmaz (chromadb uyarısı normal)
- **Skill .md dosyaları:** Kod değil, sayma
- **Sadece tabloya bakma:** CLAUDE.md/proje rehberi güncel olmayabilir, her zaman KENDİN tara
- **Çok katmanlı dizinlere dikkat:** Bir derived/fork projede aynı dosyalar birden fazla dizinde bulunabilir (root/ ve agent/ gibi). Sadece root/ seviyesine bakıp "eksik" raporu vermek yanlıştır. Her zaman tüm kaynak dizinlerini tara:
  ```bash
  # ALL source directories, not just one
  all_files = set()
  for d in [root, agent, tools, plugins]:
      for f in os.listdir(d):
          if f.endswith('.py'): all_files.add(f)
  ```
- **Hızlı cevap verme (CRITICAL):** Kullanıcıya "var/yok/eksik" raporu vermeden önce:
  1. Tüm dizinleri tara (root, agent, tools, gateway, plugins)
  2. Dosya içeriklerini karşılaştır (wc -l, diff, fonksiyon sayısı)
  3. Import zincirini kontrol et (kim neyi import ediyor?)
  4. Emin değilsen "tamam" deme, önce doğrula
  5. Hızlı cevap = hatalı cevap. Kullanıcı bunu düzeltene kadar tekrar tekrar uyarır.
