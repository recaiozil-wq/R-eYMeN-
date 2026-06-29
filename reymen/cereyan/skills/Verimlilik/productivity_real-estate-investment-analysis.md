
> **Kategori:** productivity

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Productivity_Real Estate Investment Analysis |
| **Nerede?** | productivity/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: real-estate-investment-analysis
title: Real Estate Investment Analysis
description: Generate Excel investment templates and parse property listing data for urban regeneration (kentsel dönüşüm) analysis. Covers template creation, data parsing workflow, and blocked-scraping fallback patterns. Includes Playwright + Chrome profile/cookie transfer fallback to evade strict bot protection.</summary>
triggers: real estate, urban regeneration, kentsel dönüşüm, investment template, Excel, openpyxl, property listing, arsa payı, emsal, inşaat maliyeti, data parser, dump veri

audience: user
tags: [productivity, tools]
category: productivity---

# Real Estate Investment Analysis Skill

## When to Use
- User asks for a property investment Excel template/analysis
- User provides raw HTML/text from blocked real estate listing sites (sahibinden.com, etc.)
- Need to calculate unit cost, potential profit, construction cost impact, and emsal multiplier
- Urban regeneration (kentsel dönüşüm) yield analysis in Turkey/Istanbul

## Mandatory Workflow: Data Parser Mode
- If a platform blocks automatic scraping, **do not retry** in fetch/browser loops.
- Immediately switch to **Data Parser mode**: wait for user-provided raw HTML/text dump.
- Parse the dump locally, extract fields, and write directly into the Excel template.
- Reuse the latest template file: `Kentsel-Donusum-Yatirim-Sablonu.xlsx` in the user's Obsidian Hermes folder.

## Template Structure (2 Sheets)

### Sheet 1: Yatırım Şablonu (Investment Template)
Columns (manual input marked with *):
1. İlçe/Mahalle
2. İlan Başlığı & Link*
3. Mevcut Fiyat (TL)*
4. Arsa Payı (m²)*
5. Birim Maliyet (TL/m²) = `=IF(E8>0,D8/C8,0)`
6. Bölge Sıfır m² Fiyatı (TL)*
7. Potansiyel Kar (%) = `=IF(F8>0,(G8-E8)/E8,0)`

### Sheet 2: Analiz Kriterleri (Analysis Criteria)
Rows:
- Kriter, Açıklama, Eşik Değer, Durum, İnşaat Maliyeti Dikkate Alınsın mı?, Emsal Artışı Kontrolü, Risk Taraması Kralı
- Key criteria:
  - Arsa Payı Oranı: ≥25 m²
  - Bina Yaşı: ≥25 yıl
  - Potansiyel Kar: %150+
  - Birim Maliyet: Below district average
  - Risk Durumu: Clean / Encumbered
  - Kentsel Dönüşüm Statüsü: Municipality approved

## Visual Style Rules
- Header fill: `1F4E79` (dark blue), white bold font
- Accent: `00BCD4` (turquoise)
- Zebra rows: `E8F6F8` / `FFFFFF`
- Borders: thin on all sides
- Column widths:
  - A:18, B:40, C:18, D:14, E:18, F:22, G:16 (Sheet 1)
- Cell alignment: vertical center, wrap text
- Footer centered, color `888888`, italic

## Data Parsing Rules
- Accept only 3 fields from user: Konum | Fiyat (TL) | Arsa Payı (m²)
- Link is optional; other fields are left empty if not provided.
- Write only into rows 6-15 of Sheet 1 (rows 1-5 reserved for header/example).
- Do not add new derived columns or extra metadata.
- Use Turkish number format: `#,##0` for TL, `0` for integer m², `0.0%` for percentages.
- Do not hallucinate missing fields; if a field is absent in the dump, leave the cell empty.

## Environment Notes
- Use Python 3.14 at: `C:\\Users\\marko\\AppData\\Local\\Python\\PythonCore-3.14-64\\python.exe`
- openpyxl required; install if missing.
- Template path: `C:\\Users\\marko\\OneDrive\\Belgeler\\Obsidian Vault\\Hermes\\Kentsel-Donusum-Yatirim-Sablonu.xlsx`

## Anti-Bot Fallback: Playwright + Chrome Profile
- **HARD RULE**: When a listing site shows bot walls (`Reference ID` / captcha / 504 on details), scraping loops are banned. First apply the existing Data Parser mode.
- If the user still wants site navigation, the supported fallback is Playwright with a real Chrome profile:
  1. Close all normal Chrome windows so the profile is unlocked.
  2. **PREFER**: Use Playwright's own Chromium with `cookies.json` injected via `context.add_cookies(...)`.
  3. **IF** `Chrome User Data` is missing or Chrome is not installed, fallback to installed Playwright Chromium; do **NOT** try `playwright install chrome` as a primary step.
  4. Use `headless=False` so the user can complete any presented captcha manually.
- The shared script is at: `C:\Users\marko\AppData\Local\hermes\scripts\sahibinden_with_chrome_profile.py`
- Do not chain multiple fetch retries or browser-install loops when the bot wall is solid; stop and report the durable fallback instead.

## Pitfalls
- **Formula mismatch user fix**: User reverted to 7-column layout. Keep columns C-G only. No extra cost/emsal columns in Sheet 1.
- **Scraping loops**: User explicitly banned automatic retry loops on 504/bot-block pages. Parser mode is mandatory fallback.
- **Chrome User Data missing**: On this machine Chrome may be absent. Detect `~\AppData\Local\Google\Chrome\User Data`; if missing, do not block on creating folders. Use cookies.json + Playwright Chromium instead.
