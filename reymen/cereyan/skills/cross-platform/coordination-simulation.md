
> **Kategori:** references

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Coordination Simulation |
| **Nerede?** | references/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Koordinasyon Simülasyonu — 2026-06-21

## Senaryo

Ağda şüpheli port (TCP/4444) tespit edildi. Kali ajanı tespit eder, Windows ajanı engeller.

## Ham Log

```
ADIM 1: KALI (tespit)
  nmap -sV -p 1-65535 localhost
  → TCP/4444 suspicious-service (unknown)
  → 1 LLM çağrısı (ilk tarama, hafızada kayıt yoktu)
  → {cmd: BLOCK_PORT, port: 4444, protocol: tcp, kaynak: kali} → Windows

ADIM 2: WINDOWS (engelle)
  netstat -an | findstr :4444 → TCP 0.0.0.0:4444 LISTENING (doğrulandı)
  → ✅ HAFIZA ATLAMASI (ID=2344, guven=0.8)
  netsh advfirewall firewall add rule name="BLOCK_SUSPICIOUS_4444" dir=in action=block protocol=tcp localport=4444
  → ✅ HAFIZA ATLAMASI (ID=2342, guven=0.9)
  → {cmd: PORT_BLOCKED, port: 4444, durum: engellendi, kaynak: windows} → Kali

ADIM 3: KALI (onay)
  nmap -p 4444 localhost → 4444/tcp filtered
  → ✅ PORT BASARIYLA ENGELLENDI
  → ✅ HAFIZA ATLAMASI (ID=2343, guven=0.9)

ADIM 4: HAFIZA KAYDI
  → cross-platform/security eklendi, guven=1.0
```

## Maliyet Analizi

| Adım | LLM Çağrısı | Hafıza Atlaması | Süre |
|:----:|:-----------:|:---------------:|:----:|
| Kali tespit | 1 | 0 | ~1sn |
| Windows engelle | 0 | 2 | ~1sn |
| Kali onay | 0 | 1 | ~1sn |
| **Toplam** | **1** | **3** | **~3sn** |

## DB'ye Eklenen Kayıtlar

| Anahtar | Kategori | Güven |
|:--------|:---------|:-----:|
| windows firewall kurali | windows/terminal/network | 0.9 |
| kali windows koordinasyon port engelleme | cross-platform/security | 0.9 |
| netsh port tarama dogrulama | windows/terminal/network | 0.8 |
| kali windows port engelleme koordinasyonu | cross-platform/security | 1.0 |
