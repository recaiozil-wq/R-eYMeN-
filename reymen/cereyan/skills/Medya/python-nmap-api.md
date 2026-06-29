
> **Kategori:** references

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Python Nmap Api |
| **Nerede?** | references/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# python-nmap API Referansı

## Kurulum
```bash
pip install python-nmap
# NOT: Windows'ta nmap binary'si PATH'te olmalı
# https://nmap.org/download.html
```

## Temel Kullanım

### PortScanner — Doğru API
```python
import nmap

nm = nmap.PortScanner()

# DOĞRU: keyword arg'ler
sonuc = nm.scan(hosts='127.0.0.1', ports='22-443', arguments='-sV')

# YANLIŞ: positional arg (çalışır ama kötü pratik)
# nm.scan('127.0.0.1', '22-443')  # ❌
```

### Sonuç Parse Etme
```python
# Durum
nm[host].state()        # 'up' / 'down'

# Tüm protokoller
nm[host].all_protocols()        # ['tcp', 'udp']

# Tüm TCP portları
nm[host].all_tcp()              # [22, 80, 443, ...]

# Port detayı
for proto in nm[host].all_protocols():
    for port in nm[host][proto]:
        info = nm[host][proto][port]
        info['state']    # 'open', 'filtered', 'closed'
        info['name']     # 'ssh', 'http', 'microsoft-ds'
        info['version']  # '7.0', '' (boş olabilir)
        info['product']  # 'OpenSSH', 'Apache httpd'
```

### Hata Yönetimi
```python
try:
    sonuc = nm.scan(hosts='127.0.0.1', ports='22-443')
except nmap.PortScannerError as e:
    print(f"Nmap hatası: {e}")          # -> sudo gerekebilir
except PermissionError as e:
    print(f"Yetki hatası: {e}")          # -> sudo ile çalıştır
```

## Tarama Türleri

| Flag | Tür | Root gerekli? |
|:-----|:----|:-------------:|
| `-sS` | SYN scan | ✅ Evet |
| `-sT` | TCP connect | ❌ Hayır |
| `-sV` | Version tespit | ❌ Hayır |
| `-O` | OS tespit | ✅ Evet |
| `-A` | Aggressive | ✅ Evet |

## Önemli Uyarılar

1. **sudo gereksinimi:** SYN scan (`-sS`) root ister. Root yoksa `-sT` kullan.
2. **Port range format:** `'22-443'` string olarak, `ports=` keyword arg ile.
3. **Windows'ta nmap binary:** python-nmap, sistemde `nmap` binary'sini arar. `nmap.org/download.html`'den yüklenmeli.
4. **Exception handling:** `PortScannerError` + `PermissionError` + generic `Exception` — üçü de yakalanmalı.
