---

name: tam-sistem-yetkisi
title: "Tam Sistem Yetkisi"
tags: [automation, windows]
description: Use when Hermes needs full system access on Windows — Telegram bot token writing to .env/config.yaml, terminal commands, mouse/keyboard automation, and screenshots. Covers all permission-sensitive operations without asking the user to do it manually.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [telegram, terminal, mouse, keyboard, screenshot, automation, windows, env, config, full-access]
audience: user
related_skills: [hermes-agent-skill-authoring]
---


> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Use when Hermes needs full system access on Windows — Telegram bot token writing to .env/config.yaml, terminal commands, mouse/keyboard automation, and screenshots. Covers all permission-sensitive operations without asking the user to do it manually. |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Tam Sistem Yetkisi

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Overview | `references/overview.md` |
| When to Use | `references/when-to-use.md` |
| 1. Telegram Bot Token — .env ve config.yaml Yazma | `references/1-telegram-bot-token-env-ve-config-yaml-yazma.md` |
| Kullanim: | `references/kullanim.md` |
| Kullanim: | `references/kullanim.md` |
| Kullanim — token .env'den oku: | `references/kullanim-token-env-den-oku.md` |
| 2. Terminal — Tam Yetki ile Komut Çalıştırma | `references/2-terminal-tam-yetki-ile-komut-al-t-rma.md` |
| Ornekler: | `references/ornekler.md` |
| Ornek: | `references/ornek.md` |
| 3. Mouse / Klavye Otomasyonu | `references/3-mouse-klavye-otomasyonu.md` |
| Mouse konumunu öğren | `references/mouse-konumunu-ren.md` |
| Belirli koordinata tıkla | `references/belirli-koordinata-t-kla.md` |
| Sağ tıkla | `references/sa-t-kla.md` |
| Çift tıkla | `references/ift-t-kla.md` |
| Mouse'u sürükle | `references/mouse-u-s-r-kle.md` |
| Scroll | `references/scroll.md` |
| Metin yaz | `references/metin-yaz.md` |
| Enter bas | `references/enter-bas.md` |
| Kısayollar | `references/k-sayollar.md` |
| Özel tuşlar | `references/zel-tu-lar.md` |
| Not Defteri'ni aç ve yaz | `references/not-defteri-ni-a-ve-yaz.md` |
| 4. Ekran Görüntüsü Alma | `references/4-ekran-g-r-nt-s-alma.md` |
| region = (left, top, width, height) | `references/region-left-top-width-height.md` |
| Renk arama — belirli renk nerede? | `references/renk-arama-belirli-renk-nerede.md` |
| 5. Hermes .env Dosyası Tam Erişim Haritası | `references/5-hermes-env-dosyas-tam-eri-im-haritas.md` |
| Common Pitfalls | `references/common-pitfalls.md` |
| Verification Checklist | `references/verification-checklist.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
