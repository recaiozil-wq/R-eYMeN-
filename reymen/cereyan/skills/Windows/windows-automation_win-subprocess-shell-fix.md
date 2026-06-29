
> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Windows Automation_Win Subprocess Shell Fix |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: win-subprocess-shell-fix
description: Windows'ta komutları subprocess.run ile çalıştırırken tam yol ve shell=True kullanma kuralı.
title: "Win Subprocess Shell Fix"
version: 1.0

audience: user
tags: [automation, windows]
category: windows-automation---
# Windows'ta Subprocess Komut Çalıştırma Kuralı

Windows'ta PATH'te olmayan komutları (npm ile kurulmuş `claude`, `ollama.exe` vb.) Python `subprocess.run` ile çalıştırırken:

- Tam dosya yolunu kullan (ör: `C:\Users\marko\AppData\Roaming\npm\claude.cmd`)
- `shell=True` ekle
- `capture_output=True`, `text=True`, `timeout=120` standart parametrelerdir

## Örnekler

```python
import subprocess

# Claude Code
def ask_claude(prompt):
    r = subprocess.run(
        [r"C:\Users\marko\AppData\Roaming\npm\claude.cmd", "-p", prompt],
        capture_output=True,
        text=True,
        timeout=120,
        shell=True
    )
    return (r.stdout or r.stderr).strip()

# Ollama
def ask_ollama(prompt):
    OLLAMA_MODEL = "dolphin-llama3:latest"
    r = subprocess.run(
        [r"C:\Users\marko\AppData\Local\Programs\Ollama\ollama.exe", "run", OLLAMA_MODEL, prompt],
        capture_output=True,
        text=True,
        timeout=120,
        shell=True
    )
    return (r.stdout or r.stderr).strip()
```

## Neden?

Windows'ta `subprocess.Popen` komut listesiyle çalıştırırken:
1. PATH arama davranışı farklı çalışabilir
2. `.cmd` uzantılı npm paketleri shell bağlamı gerektirir
3. `shell=True` olmadan `WinError 2` (dosya bulunamadı) alınır

## Doğrulama

```bash
where claude
where ollama
```

Çıktıdan gelen tam yolları kullan.