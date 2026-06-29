---
name: otonom-cozum-dongusu
title: "Otonom Cozum Dongusu"
tags: [agents, ai]
description: Use when any problem needs to be solved autonomously without user intervention. Takes a problem description, uses llava to see the screen, dolphin-llama3 to generate Python code, runs it in VS Code, analyzes output, and loops until solved. Saves successful solutions as skills automatically.
version: 1.0.0
author: marko
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [autonomous, loop, dolphin, llava, vscode, problem-solving, self-healing, dongu, otonom]
audience: user
related_skills: [vscode-otomasyon, gorsel-onaylama, screen-vision-analiz, mouse-klavye-ctypes]


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Use when any problem needs to be solved autonomously without user intervention. Takes a problem description, uses llava to see the screen, dolphin-llama3 to generate Python code, runs it in VS Code, a |
| **Nerede** | `autonomous-ai-agents\autonomous-ai-agents_otonom-cozum-dongusu.md` |
| **Ne Zaman** | Ilgili gorev gerektiginde |
| **Neden** | Autonomous Ai Agents Otonom Cozum Dongusu islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Use when any problem needs to be solved autonomously without user intervention. Takes a problem description, uses llava to see the screen, dolphin-llama3 to generate Python code, runs it in VS Code, analyzes output, and loops until solved. Saves successful solutions as skills automatically. |
| **Nerede?** | autonomous-ai-agents/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: Otonom ajan gelistiricisi
Ne: Use when any problem needs to be solved autonomously without user intervention. Takes a problem description, uses llava to see the screen, dolphin-llama3 to generate Python code, runs it in VS Code, a
Nerede: `autonomous-ai-agents\autonomous-ai-agents_otonom-cozum-dongusu.md`
Ne Zaman: Ilgili gorev gerektiginde
Neden: Autonomous Ai Agents Otonom Cozum Dongusu islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Otonom Cozum Dongusu

## Overview

Herhangi bir sorunu insan mudahalesi olmadan cozer:

```
Problem tanimi
    ↓
llava → ekran analizi (gorsel baglam)
    ↓
dolphin-llama3 → Python kodu uretir
    ↓
VS Code → kodu calistirir
    ↓
Cikti → dolphin'e gonderilir
    ↓
Hata varsa → dolphin duzeltir → tekrar calistirir
    ↓ (basarana kadar)
Basarili cozum → skill olarak kaydedilir
```

## When to Use

- "Bu sorunu otomatik coz"
- "Hatayi kendisi duzeltsin"
- Herhangi bir Python ile cozulebilecek problem
- Tekrar eden hata-duzeltme donguleri
- Cozum bulununca skill olarak kalicilastirma

Don't use for: Kullanici onay gerektiren kritik islemler.

## Hard Pre-Check Rule

Before generating or running any solution, ALWAYS:

1. Search Hermes skills for an existing applicable rule.
2. Search the Obsidian vault for an existing note/skill on the topic.
3. If a relevant item exists, reuse it verbatim and do not re-create the solution.

"Every user request" means every task invocation, not only long-running ones.

### Pitfall: Skipping the Check
The most common failure mode is jumping straight to implementation. If the user ever corrects this with phrases like "skill veya Obsidian var mi diye kontrol et yapmadan once" or "bu bir kuraldır", treat it as a FIRST-CLASS signal. The pre-check is non-negotiable and must be the very first action, before any tool call that creates or writes anything.

## Model Routing

- Primary model: `stepfun/step-3.7-flash:free`
- Dolphin fallback: `dolphin-llama3` — reserved for requests the primary model refuses, policy-bounded topics, or autonomous recovery paths that explicitly require the fallback.
- After a `dolphin-llama3` task finishes, return execution to the primary model automatically.

## Stratejik Ajan Secici (Multi-Persona)

Hata alındığında, LLM çağrısı yapmadan kural tabanlı olarak **milisaniyelerde** en uygun uzman persona'ya geç. Aynı modelin farklı sistem prompt'larla çağrılmasıdır — ek LLM bağlantısı gerekmez, sadece `sistem_talimati` prompt'u değişir.

### 5 Persona

| Persona | Ne Zaman | Hata Desenleri |
|---------|----------|---------------|
| `genel_cozucu` | Varsayılan, eşleşme yoksa | — |
| `kod_uzmani` | Syntax, import, type, attribute hataları | `syntaxerror`, `nameerror`, `typeerror`, `importerror`, `traceback` |
| `sistem_mimari` | Dosya, bağlantı, zaman aşımı | `filenotfounderror`, `connectionerror`, `timeout`, `econnrefused` |
| `guvenlik_uzmani` | Yetki, API anahtarı, SSL | `authentication`, `forbidden`, `ssl`, `ratelimit` |
| `veri_uzmani` | Veritabanı, JSON/YAML, encoding | `database`, `jsondecode`, `encoding`, `sqlite` |

### Kullanim

```python
from akilli_yonlendirici import stratejik_ajan_sec, ajan_talimatini_getir

yeni_ajan = stratejik_ajan_sec(mevcut_ajan, hata_mesaji)
if yeni_ajan != mevcut_ajan:
    yeni_talimat = ajan_talimatini_getir(yeni_ajan)
    # Yeni talimatla LLM'i tekrar cagir
```

### Kural

- Saf regex+kural tabanli, milisaniyelerde karar verir, LLM cagrisi yapmaz.
- Hata eslesmezse mevcut ajani korur.
- 30+ hata deseni tanir. Detay: `references/persona-detay.md`\nDetayli gorev formati: `references/yapilandirilmis-gorev-formati.md`\nModul entegrasyon patterni: `references/hermes-modul-entegrasyonu.md`\n\n## Cokus Raporlayici (Crash Report)

Otonom cozum sinirlari tukendiginde (max_tur asildi, tum ajanlar basarisiz oldu) insan-okunabilir crash raporu uret ve kullaniciya devret.

### Kullanim

```python
from cokus_raporlayici import cokus_raporu_uret

rapor = cokus_raporu_uret(
    gorev="Web'den veri cek",
    deneme_sayisi=10,
    hata_gecmisi=["[genel] HTTP 403", "[kod] SyntaxError"],
    denenen_ajanlar=["genel_cozucu", "kod_uzmani"],
    tiklanma_nedeni="API rate limit asildi"
)
# Rapor .ReYMeN/cokus_raporlari/ klasorune kaydedilir
```

### Rapor icerigi
- Kronolojik hata kaydi
- Denenen tum ajanlar
- Kok neden analizi
- Kullaniciya gorev devri protokolu ("su adimlari izle, su bagimliligi duzelt")

### Ne Zaman

- `max_tur` asildi ve hala cozum yok
- Tum 5 persona denendi ve basarisiz oldu
- LLM ayni hatayi 3+ kez tekrarladi

## Autonomous Execution Contract

- Be decisive: run solution candidates, inspect the result, and iterate without asking the user to confirm.
- After scripted Windows interactions and artifact delivery, verify the result exists before declaring success.
- Screen or camera captures must be freshly generated before sending; if an artifact path is reused, validate its current modification time or size.

---

## Kullanim

```bash
# Herhangi bir problem
python C:\Users\marko\hermesloop.py "problem tanimi" --turns 8

# Tor baglanti sorunu
python C:\Users\marko\hermesloop.py --tor

# Daha fazla tur (zor problemler)
python C:\Users\marko\hermesloop.py "karmasik problem" --turns 15

# Basit kontrol
python C:\Users\marko\hermesloop.py "Python ile port 9150 kontrol et"
```

---

## Dongu Adımlari (Detay)

### Adim 1: Ekran Analizi
```python
screen_ctx = llava_analyze(
    f"Bu ekranda ne gorunuyor? Problem: '{problem}'"
)
```
llava-llama3 mevcut ekran durumunu anlatiyor.

### Adim 2: Kod Uretme
```python
response = dolphin(problem + ekran_durumu, SYSTEM_PROMPT)
kod = extract_code(response)
```
dolphin-llama3 calistirilabilir Python kodu uretir.

### Adim 3: Calistirma
```python
rc, stdout, stderr = run_code(kod, filename)
# VS Code'da da acilir (gorsel takip icin)
```

### Adim 4: Basari Kontrolu
```python
if rc == 0 and not stderr:
    save_skill(problem, kod, tur)
    return True   # DONGU BITTI
```

### Adim 5: Hata Durumunda
```python
# Tekrar ekran al
screen_after = llava_analyze("Hata mesaji ne yazıyor?")

# dolphin'e duzeltme sor
fix_response = dolphin(
    f"Calismayan kod:\n{kod}\n\nHata:\n{stderr}\n\nDuzelt."
)
kod = extract_code(fix_response)
# → Adim 3'e don
```

---

## Gercek Test Sonucu

```
Problem: "Python ile port 9150 SOCKS5 baglantisi kontrol et"

Tur 1:
  dolphin → 458 karakter kod uretti
  rc=0, stdout: "Baglanti yapmak icin zaman asimina neden oldu..."
  → BASARILI (1. turda!)

Skill kaydedildi: autonomous-ai-agents/auto-python-ile-port-9150...
Obsidian: Hermes/Skills/autonomous-ai-agents/ altina eklendi
```

---

## Otomatik Skill Kaydetme

Her basarili cozum otomatik kaydedilir:

```
~/.hermes/skills/autonomous-ai-agents/auto-<slug>/SKILL.md
Obsidian: Hermes/Skills/autonomous-ai-agents/auto-<slug>.md
```

Cozulemeyenler de kaydedilir ([COZULEMEDI] prefix ile).

---

## Python API

```python
import sys
sys.path.insert(0, r"C:\Users\marko")
import hermesloop as hl

# Herhangi bir problemi coz
ok = hl.autonomous_loop(
    "wifi aglarini tara ve listele",
    max_turns=5
)

# Kod uretme
dolphin_cevap = hl.dolphin("Bu kodu yaz: ...")
kod = hl.extract_code(dolphin_cevap)

# Kodu calistir
rc, out, err = hl.run_code(kod)

# Ekran analizi
screen = hl.llava_analyze("Ekranda ne var?")
```

---

## Common Pitfalls

1. **dolphin yanlis kod uretirse** — Turns artir, daha specific problem tanimi yaz.
2. **llava ekrani anlayamazsa** — Problem tanimi daha net yaz, llava baglam oluyor.
3. **Tor sorunu** — `--tor` modu kullan, Tor Browser yolu skill'de taninmis.
4. **Cok uzun suruyor** — `--turns 3` ile hizli test, basarisizsa artir.
5. **Skill kaydedilmedi** — Obsidian klasoru kontrol et: `Hermes/Skills/autonomous-ai-agents/`.

## Verification Checklist

- [ ] `python hermesloop.py "basit test" --turns 2` calisti
- [ ] VS Code'da kod acildi
- [ ] Skill Obsidian'da gorunuyor
- [ ] dolphin Turkce problem anladi
- [ ] llava ekran analizi yapti
