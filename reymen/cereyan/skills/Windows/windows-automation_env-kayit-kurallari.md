---
name: env-kayit-kurallari
title: "Env Kayit Kurallari"
tags: [automation, windows]
description: Use FIRST before any configuration, API key, or settings task. Contains all .env file locations, key names, and the rule that .env is the single source of truth. Every .env change must be saved to Obsidian automatically. Check this skill before reading/writing any config.
version: 1.0.0
author: marko
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [env, config, api-key, token, obsidian, kayit, oncelik, source-of-truth, kalici]
audience: user
related_skills: [obsidian-vault-kurallari, tam-sistem-yetkisi, obsidian]
---


> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Use FIRST before any configuration, API key, or settings task. Contains all .env file locations, key names, and the rule that .env is the single source of truth. Every .env change must be saved to Obsidian automatically. Check this skill before reading/writing any config. |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# .env Kayıt Kuralları — Öncelik ve Kalıcı Hafıza

## KURAL 1 — .env İLK KONTROL YERİDİR

Herhangi bir ayar, API anahtarı veya token gerektiğinde:
```
1. ÖNCE .env dosyasını oku
2. Sonra config.yaml'a bak
3. En son SOUL.md'e bak
```

**HİÇBİR ZAMAN** token/key değerini başka yerden tahmin etme veya hard-code etme.

---

## .env Dosya Konumları (KESİN)

```
Hermes Agent .env (CLI):
  C:\Users\marko\AppData\Local\hermes\.env

Hermes Gateway .env (ÖNCELİKLİ — gateway burayı okur):
  C:\Users\marko\.hermes\.env          (*~/.hermes/.env)
  NOT: Gateway her zaman önce ~/.hermes/.env'yi okur.
       AppData/.env'deki ayarlar buraya da kopyalanmalıdır.
       Yoksa oluşturulmalıdır.

hermes.py (özel sistem) .env:
  C:\Users\marko\hermes-ai\.env

hermes-ai yapılandırma:
  C:\Users\marko\AppData\Local\hermes\config.yaml
```

Obsidian yansımaları (maskeli, güncel):
```
C:\Users\marko\OneDrive\Belgeler\Obsidian Vault\Hermes\env-hermes-agent.md
C:\Users\marko\OneDrive\Belgeler\Obsidian Vault\Hermes\env-hermes-ai.md
```

---

## Hermes Agent .env — Anahtar Listesi

| Anahtar | Açıklama |
|---------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot bağlantısı |
| `TELEGRAM_ALLOWED_USERS` | İzinli kullanıcı ID'leri (NOT: `ALLOWLIST` değil, `ALLOWED_USERS`) |
| `GATEWAY_ALLOW_ALL_USERS` | `true` yapılırsa gateway tüm kullanıcılara izin verir (yedek) |
| `DEEPSEEK_API_KEY` | DeepSeek / Nous erişim |
| `NOUS_API_KEY` | Nous Portal API |
| `GOOGLE_API_KEY` | Google AI / Gemini |
| `GEMINI_API_KEY` | Gemini (Google_API_KEY ile aynı) |
| `OBSIDIAN_VAULT_PATH` | `C:\Users\marko\OneDrive\Belgeler\Obsidian Vault` |
| `TERMINAL_TIMEOUT` | Terminal komut zaman aşımı (saniye) |

## hermes-ai .env — Anahtar Listesi

| Anahtar | Değer |
|---------|-------|
| `DEEPSEEK_API_KEY` | DeepSeek / Nous API |
| `OBSIDIAN_VAULT` | `C:\Users\marko\OneDrive\Belgeler\Obsidian Vault` |
| `OLLAMA_MODEL` | `dolphin-llama3` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` |

---

## KURAL 2 — .env Değişince Obsidian'a Yaz

Her `.env` değişikliğinden sonra şu komutu çalıştır:

```bash
"C:\Users\marko\hermes-ai\venv\Scripts\python.exe" "C:\Users\marko\hermes-ai\env_watcher.py"
```

Veya arka planda sürekli izle:
```bash
# Arka planda calistir (Ctrl+C ile durdur)
"C:\Users\marko\hermes-ai\venv\Scripts\python.exe" "C:\Users\marko\hermes-ai\env_watcher.py"
```

---

## KURAL 3 — .env Okuma (Python)

```python
import os
from pathlib import Path
from dotenv import load_dotenv

# Hermes Agent .env
load_dotenv(r"C:\Users\marko\AppData\Local\hermes\.env")

# Değeri oku
token = os.getenv("TELEGRAM_BOT_TOKEN", "")
key   = os.getenv("DEEPSEEK_API_KEY", "")
vault = os.getenv("OBSIDIAN_VAULT_PATH", "")

print(f"Token: {token[:10]}***")
print(f"Vault: {vault}")
```

---

## KURAL 4 — .env Yazma (Python)

```python
import re
from pathlib import Path

def set_env(env_path: str, key: str, value: str) -> None:
    p    = Path(env_path)
    text = p.read_text(encoding="utf-8") if p.exists() else ""
    pat  = re.compile(rf"^{re.escape(key)}\s*=.*", re.MULTILINE)
    new  = f"{key}={value}"
    if pat.search(text):
        text = pat.sub(new, text)
    else:
        text = text.rstrip("\n") + f"\n{new}\n"
    p.write_text(text, encoding="utf-8")
    print(f"[OK] {key} yazildi")

# Kullanim:
set_env(
    r"C:\Users\marko\AppData\Local\hermes\.env",
    "TELEGRAM_BOT_TOKEN",
    "yeni_token_buraya"
)
```

---

## KURAL 5 — Obsidian'daki env Notları

Obsidian'da şu dosyalar her zaman güncel olmalı:

- `[[env-hermes-agent]]` — Ana Hermes anahtarları (maskeli)
- `[[env-hermes-ai]]` — hermes.py anahtarları (maskeli)

Bu notlar `env_watcher.py` tarafından otomatik güncellenir.
Değerlerin tamamını görmek için gerçek `.env` dosyasını oku.

---

## Hangi .env Neyi Etkiler

```
TELEGRAM_BOT_TOKEN    → hermes gateway, Telegram mesajları
TELEGRAM_ALLOWED_USERS → gateway yetkilendirme (NOT: ALLOWLIST değil)
GATEWAY_ALLOW_ALL_USERS → gateway acil durum bypass'ı
OBSIDIAN_VAULT_PATH   → skill sync, not yazma (DOGRU YOL)
DEEPSEEK_API_KEY      → DeepSeek / Nous model erişimi
NOUS_API_KEY          → Nous Portal (stepfun/step-3.7-flash:free modeli)
GOOGLE_API_KEY        → Gemini modelleri
OLLAMA_MODEL          → Yerel model (dolphin-llama3)
KLING_ACCESS_KEY      → Kling AI video (kling.ai/dev/api-key)
KLING_SECRET_KEY      → Kling AI secret
RUNWAYML_API_KEY      → RunwayML video (key_ + 128 hex = 132 char)
```

**ÖNEMLİ:** Gateway Scheduled Task ile çalışıyorsa `~/.hermes/.env` dosyası da oluşturulmalı. Aksi halde gateway allow ayarlarını görmez ve tüm kullanıcıları unauthorized olarak reddeder.

## Common Pitfalls

1. **env_watcher.py çalışmıyor** — Docstring'de `\\U` escape hatası; `env_watcher.py` update edildi.
2. **Yanlış vault yolu** — `OBSIDIAN_VAULT_PATH` her zaman `OneDrive\\Belgeler\\Obsidian Vault`.
3. **Hermes maskeleme + env_watcher token bozma** — Hermes `read_file`, `cat` gibi araçlarla `.env` okunduğunda değerleri maskeler (`***`). Eğer bu maskelenmiş içerik `env_watcher.py` tarafından `.env`'ye geri yazılırsa, tüm token'lar bozulur. **Belirti**: `.env`'de `TELEGRAM_BOT_TOKEN=851817***9aM` gibi satırlar olması. **Çözüm**:
   - Token değişikliği sonrası env_watcher'ı çalıştırma
   - `.env` okumak için `Path(env_path).read_bytes()` (binary mode) kullan, `read_file` veya `cat` kullanma
   - Gerçek içeriği doğrulamak için: `python -c "with open(r'.env','rb') as f: print(f.read().decode())"`
4. **GITHUB_TOKEN bozulduysa** — `.env`'yi manuel düzelt veya yeniden yaz. Hermes'in maskelenmiş değerini kopyalayıp yapıştırma — her zaman orijinal token'ı kullan.
5. **Key bulunamıyor** — Önce doğru `.env` dosyasını `load_dotenv()` ile yüklediğinden emin ol.
6. **.env değişti ama Obsidian güncel değil** — `env_watcher.py` başlatılmamış olabilir.
7. **Gateway env adı farkı:** Gateway `TELEGRAM_ALLOWED_USERS` bekler. Eğer `.env`'de `TELEGRAM_ALLOWLIST` yazıyorsa gateway onu görmez ve tüm kullanıcıları unauthorized olarak reddeder. Gateway "connected" gösterir ama mesaj işlemez. **Çözüm:** Her zaman `TELEGRAM_ALLOWED_USERS` kullan, `TELEGRAM_ALLOWLIST` veya başka varyant değil.
9. **~/.hermes/.env yoksa gateway allow ayarlarını görmez:** Gateway başlarken önce `~/.hermes/.env`'yi okur. Bu dosya yoksa ana `.env`'deki ayarlar da çalışmaz. Dosyayı oluştur ve içine en azından `GATEWAY_ALLOW_ALL_USERS=true` veya `TELEGRAM_ALLOWED_USERS=...` yaz. Bu dosya Scheduled Task ile çalışan gateway için gereklidir.
10. **.env'ye yazarken f-string + *** SyntaxError:** Python f-string içinde `***` kullanmak SyntaxError'a yol açar (`f-string: expressions nested too deeply`). Çözüm: string concatenation veya normal format() kullan:
    ```python
    # YANLIŞ
    content += f'API_KEY=value={secret}'

    # DOĞRU — string concatenation
    content += 'API_KEY='
    content += secret
    content += '\n'

    # Veya heredoc
    python3 << 'PYEOF'
    path = r'path\to\.env'
    with open(path, 'a') as f:
        f.write(f'KEY=val...')
    PYEOF
    ```

## Verification Checklist

- [ ] `C:\Users\marko\AppData\Local\hermes\.env` okunabildi
- [ ] `TELEGRAM_BOT_TOKEN` boş değil
- [ ] `OBSIDIAN_VAULT_PATH` doğru yolu gösteriyor
- [ ] Obsidian'da `env-hermes-agent.md` güncel timestamp'e sahip
- [ ] `env_watcher.py` arka planda çalışıyor (veya elle tetiklendi)
