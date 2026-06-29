
> **Kategori:** references

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Hermes Import 2026 06 21 |
| **Nerede?** | references/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Hermes → ReYMeN Toplu Import

**Tarih:** 2026-06-21
**Süre:** 2.6 saniye
**Sonuç:** 125 session, 9078 mesaj → ReYMeN hafıza.db + notes/sessions/

## Nerede?
- `notes/sessions/session_import_*.md` — 125 dosya
- `hafiza.db` — 416 session toplam (eski + yeni)
- `hafiza.db` — 1351 kayit (konusmalar: 1158, beceriler: 114, notlar: 78)

## Kategorilendirme
Her session metnine göre otomatik kategorilendirildi:
- `kali` — nmap, pentest, exploit
- `dron` — drone, px4, uav
- `cad` — solidworks, autocad, 3d
- `windows` — windows, ekran, mouse, klavye
- `powerbi` — power bi, mcp
- `test` — test, pytest, unittest
- `genel` — diğer tümü

## Script
`hermes_to_reymen.py` — kök dizinde. Tekrar çalıştırılırsa dedup yapar (atlanan = daha önce işlenmiş).
