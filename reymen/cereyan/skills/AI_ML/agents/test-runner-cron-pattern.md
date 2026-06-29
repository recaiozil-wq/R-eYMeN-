
> **Kategori:** references

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Test Runner Cron Pattern |
| **Nerede?** | references/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Test Runner Cron — 15 Dakikada Bir Test

## Ne Zaman

Kullanıcı "Test 15 dak bir yap" dediğinde, otomatik test cron'u kur.

## Setup

```python
# 1. Script oluştur: profiles/reymen/scripts/test_runner.py
#    55 test koşar (~10-15sn), sonucu log'a yazar

# 2. Cron job oluştur
cronjob(
    action='create',
    name='reymen-test-runner',
    schedule='15m',
    repeat=672,  # 7 gün × 24 saat × 4 = 672 kez
    script='test_runner.py',
    no_agent=True
)
```

## Script Template

```python
#!/usr/bin/env python3
"""ReYMeN test cron — 15 dakikada bir."""
import os, subprocess, sys
from datetime import datetime

HOME = os.path.expanduser("~")
PROJECT_DIR = os.path.join(HOME, "Desktop", "Reymen Proje", "hermes_projesi")
LOG_DIR = os.path.join(HOME, "AppData", "Local", "hermes", "profiles",
                       "reymen", "cron", "output")
os.chdir(PROJECT_DIR)

ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/...", "-q", "--tb=line", "-p", "no:capture"],
    capture_output=True, text=True, timeout=60
)

print(f"🧪 Test #{run_num} — {ts}")
print(result.stdout.strip())
Sonucu log dosyasina yaz ve stdout'tan oku.

## Pitfall — `-p no:capture`

pytest `-p no:capture` olmadan çalıştırıldığında Windows'ta crash:
```
ValueError: I/O operation on closed file
```

Bunu ÖNLEMEK için her pytest cron script'inde `-p no:capture` ekle.

## 🔴 KRİTİK PITFALL — `pytest --collect-only` KULLANMA

Cron prompt'unda veya herhangi bir test öncesi `pytest --collect-only` KESİNLİKLE KULLANMA.

**Sebep:** `pytest --collect-only` test dosyalarındaki tüm import'ları çalıştırır. Herhangi bir import bloke olursa (ağ bekleme, bozuk modül, döngüsel import) `--collect-only` da hang yiyor. Sonuç: cron worker 3 dk timeout → hata → 14/30 cron hakkı boşa harcandı.

**Doğrusu:** `compile()` ile syntax kontrolü yap:

```python
import py_compile, glob, sys

errors = []
for f in glob.glob("tests/**/*.py", recursive=True):
    try:
        py_compile.compile(f, doraise=True)
    except py_compile.PyCompileError as e:
        errors.append(str(e))

if errors:
    print(f"❌ {len(errors)} syntax hatasi")
    for e in errors[:3]:
        print(f"  {e}")
else:
    print("✅ Tum test dosyalari syntax hatasiz")
```

**Neden compile() daha iyi:**
- Import'ları çalıştırmaz → hang yemez
- Sadece syntax kontrol eder → ~0.1sn
- Bloke olmaz, timeout yemez
- `--collect-only`'nin yaptığı import kontrolünü compile() yapmaz, bu bir özellik (feature) değil güvenlik ağıdır

**Test kodunu gerçekten çalıştırmak için:** Cron script'inin içinde direkt `pytest` çağır (--collect-onludeğil), timeout=60sn ile. Bu zaten script'te var. Sadece cron prompt'unda ön kontrol olarak `--collect-only` kullanma.
