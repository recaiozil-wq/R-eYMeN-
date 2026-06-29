
> **Kategori:** references

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Karar Dongusu Ornek |
| **Nerede?** | references/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

## Ornek 1 — Karar #1: Hangi Kural Ilk Uygulanmali?

**Tarih:** 21 Haziran 2026
**Baglam:** 5 muhendislik karari arasindan ilk uygulanacak kural secimi

### 1. Ne yaptin?
No Goblins kuralini ilk siraya koydum. Diger 4 kural (Cave Mode, Karar Dongusu, Side Quest, Status Line) No Goblins olmadan islevsiz.

### 2. Neden?
Disiplin olmadan arac anlamsiz. Once gereksiz is yapmayi birak, sonra kalan araclari konuslandir.

### 3. Alternatif dusundun mu?
- **Karar Dongusu ilk:** Kayit mekanizmasi kurulsun ama goblin yapmaya devam edersen kaydin anlami kalmaz.
- **Concise Mode ilk:** Kisa konus ama gereksiz is yapmaya devam et. Tersi daha mantikli.
- **Side Quest ilk:** Yan gorevleri ayir ama ana thread'de goblin yapiyorsan fark etmez.

**Sonuc:** Once disiplin (No Goblins), sonra araclar.

---

## Ornek 2 — Karar #2: RPG Sorusu Cozum Yaklasimi

**Tarih:** 21 Haziran 2026
**Baglam:** 3 agacli RPG skill optimizasyon sorusu

### 1. Ne yaptin?
Ilk seferde kafadan n² formulu urettim. Kullanici duzeltti: her skill +1 bonus, toplam 7.

### 2. Neden?
execute_code ile brute force yapmaliydim. Tum olasiliklari tarayip dogru sonucu bulurdum.

### 3. Alternatif dusundun mu?
- **Kafadan cozum:** n² formulu uydurdum → yanlis cikti.
- **Brute force:** execute_code ile tum (a,b,g) kombinasyonlarini denerdim → dogru sonuc + kanit.

**Sonuc:** Her zaman once execute_code brute force, sonra cevap.

---

## Ornek 3 — Karar #3: YouTube Video Talimatlarini Uygulama

**Tarih:** 21 Haziran 2026
**Baglam:** "I Connected Claude to Power BI" videosu — 6 adimli talimat seti

### 1. Ne yaptin?
Transcript alindi (328 satir), 6 talimat cikarildi. Power BI MCP server kurulumu + Power BI Desktop gerektigi icin 1. adimda takildi.

### 2. Neden?
Power BI Desktop sistemde yok. MCP server (powerbi-modeling-mcp) npm'de bulunamadi. Gerekli altyapi olmadan adimlar uygulanamaz.

### 3. Alternatif dusundun mu?
- **MCP server'i manuel kur:** Kaynak kod varsa build et. Ama npm'de yayinda degil — ozel repo olabilir.
- **Alternatif MCP dene:** Farkli bir Power BI MCP var mi kontrol et.
- **Power BI Web kullan:** Power BI Service uzerinden REST API ile baglan. Ama video Desktop gosteriyor.

**Sonuc:** Altyapi eksik → uygulanamadi. Power BI kurulumu + MCP server temini sonraki adim.
