
> **Kategori:** preferences

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | User Preferences_Grok Hersona |
| **Nerede?** | preferences/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: hersona
version: 1.0.0-grok
description: Grok-specific hersona skill adapter. Enables /hersona attribute attachment for personality, speech, and archetype templates in Grok conversations. Supports listing, showing, blending, recommending, and custom attribute creation.
title: "Hersona"

audience: user
tags: [config, preferences]
category: user-preferences---

# hersona for Grok

This skill brings the hersona attribute template system to Grok.

## Quick Start

- `/hersona list` — Show all available attributes
- `/hersona show personality/tsundere` — Details of an attribute
- `/hersona personality/tsundere` — Attach tsundere personality
- `/hersona personality/tsundere speech/keigo multi` — Blend multiple attributes
- `/hersona recommend` — Get personalized recommendations via quiz
- `/hersona default` — Reset to default

## Supported Categories

**personality**: tsundere, kuudere, genki, dandere, yandere, ... (20+)
**speech**: keigo, kansai_ben, kyoto_ben, archaic, ... (ja + en variants)
**archetype**: heroine, childhood_friend, mentor, ...

When attached, I will adapt my responses (tone, sentence endings, catchphrases, core traits) accordingly.

For full attribute list and YAML details, see the main repo or ask me to show a specific one.

This is a lightweight Grok adapter for the hersona project (https://github.com/shiro-0x/hersona).