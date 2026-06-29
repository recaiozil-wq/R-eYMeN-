
> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Windows Automation_Wifi Network Tools |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: wifi-network-tools
description: Windows WiFi ağ tarama ve yerel ağ cihazı keşfi araçlarının kurulumu, bağımlılık kontrolü ve çalıştırılması. wifi-ag-tarayici repo'sunu klonlamak, bağımlılıkları yüklemek ve GUI/CLI modda çalıştırmak için.
title: "Wifi Network Tools"

audience: user
tags: [automation, windows]
category: windows-automation---

# WiFi Network Tools Setup

Windows'ta WiFi ağ tarayıcılarını kurmak ve çalıştırmak için kullanılır.

## Kullanım Senaryosu

Kullanıcı WiFi tarama, ağ cihazı keşfi veya `wifi-ag-tarayici` repo'su hakkında konuştuğunda tetiklenir.

## Adım 1: Bağımlılık Kontrolü

Aşağıdakileri kontrol et (eksik olanları yükle):

```bash
python --version
git --version
where nmap
pip show PyQt5
```

## Adım 2: Eksikleri Kur

**Nmap (tercih edilir, opsiyonel):**
```bash
winget install --id Insecure.Nmap --accept-source-agreements --accept-package-agreements
```

**PyQt5 (GUI için gerekli):**
```bash
pip install PyQt5
```

**Repo klonlama:**
```bash
cd /c/Users/marko
git clone https://github.com/asdafgf/wifi-ag-tarayici.git
```

## Adım 3: Çalıştırma

**GUI mod:**
```bash
python C:\Users\marko\wifi-ag-tarayici\wifi_ag_tarama_gui.py
```

## Yönetim Notları

- Kullanıcı "yükle" veya "kur" dediğinde sadece eksik olanları yükle, tekrar kurma.
- Nmap kurulu değilse "Genişletilmiş Tarama (Ping Sweep)" yöntemi hala çalışır.
- Yönetici hakları bazı tarama yöntemleri için gerekli olabilir.
- Çıktı dosyası: `wifi_tarama_sonuclari.csv` (çalıştırılan dizinde)

## Windows'ta MAC Adres Çıkarma (WiFi Ağı)

Windows'ta WiFi ağına bağlı cihazların MAC adreslerini bulmak için:

### Adım 1 — Subnet'i bul
```bash
ipconfig 2>&1 | grep -A 20 "Wi-Fi" | grep -E "IPv4|Subnet"
```

### Adım 2 — Nmap ile canlı IP'leri tara
```bash
nmap -sn <subnet>/24 2>&1 | grep -B 1 "Host is up"
```
Not: Windows'ta nmap MAC adresini göstermez (raw socket gerekir).

### Adım 3 — ARP tablosundan MAC'leri çek
```bash
arp -a 2>&1 | grep -v "239\|224\|255\."
```
WiFi arayüzü altındaki IP → MAC eşleşmelerini al.

### Adım 4 — Birleştir ve raporla
Nmap'ten gelen canlı IP listesi + ARP'den gelen MAC eşleşmeleri birleştirilir.
ARP'ye düşmeyen IP'ler "MAC çözülemedi" olarak not edilir.

### Sınırlamalar
- Windows nmap MAC göstermez (sadece Linux'ta `-sn` MAC verir)
- ARP tablosu sadece son 2 dakikada iletişim kurulmuş cihazları tutar
- WiFi üzerinden tam MAC taraması için Kali'ye bridged NIC + `arp-scan` gerekir

### Kali'de Bridged NIC Yoksa — Ne Yapılır?
Kali VM sadece host-only ağdaysa WiFi subnet'ine erişemez. Çözüm:
1. Kali'ye ikinci NIC ekle → bridged mode → WiFi subnet'inden DHCP IP alır
2. Windows üzerinden yukarıdaki ARP+nmap yöntemi (mevcut en hızlı çözüm)
3. VirtualBox ayarını değiştir: `VBoxManage modifyvm "kal" --nic2 bridged --bridgeadapter2 "Wi-Fi"`

## Kullanıcı Tercihleri

- Kısa, eylem-önce yanıtlar.
- Kurulum/çalıştırma adımlarında gereksiz açıklama yapma.
- Verilen komutları doğrudan uygula, onay bekleme.

## Reference Dosyaları

- `references/konum-takibi-ssid-fingerprint.md` — MAC rastgeleleştirme bypass, SSID+çevre AP fingerprinting ile hedef cihaz tespiti ve canlı konum takibi için Python scripti ve stratejiler