
> **Kategori:** references

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Live Test Output |
| **Nerede?** | references/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Canlı Test Çıktıları (21 Haziran 2026)

## ipconfig /all

```
Windows IP Configuration

   Host Name . . . . . . . . . . . . : DESKTOP-XXXX
   Primary Dns Suffix  . . . . . . . :
   Node Type . . . . . . . . . . . . : Hybrid
   IP Routing Enabled. . . . . . . . : No
   WINS Proxy Enabled. . . . . . . . : No

Wireless LAN adapter Wi-Fi:

   Connection-specific DNS Suffix  . : home
   Description . . . . . . . . . . . : Intel(R) Wi-Fi 6 AX201
   Physical Address. . . . . . . . . : XX-XX-XX-XX-XX-XX
   DHCP Enabled. . . . . . . . . . . : Yes
   Autoconfiguration Enabled . . . . : Yes
   IPv4 Address. . . . . . . . . . . : 192.168.0.20(Preferred)
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
   Lease Obtained. . . . . . . . . . : 21 Haziran 2026 18:55
   Lease Expires . . . . . . . . . . : 22 Haziran 2026 18:55
   Default Gateway . . . . . . . . . : 192.168.0.1
   DHCP Server . . . . . . . . . . . : 192.168.0.1
   DNS Servers . . . . . . . . . . . : 8.8.8.8
                                       8.8.4.4
   NetBIOS over Tcpip. . . . . . . . : Enabled

Ethernet adapter Ethernet:

   Media State . . . . . . . . . . . : Media disconnected
   Description . . . . . . . . . . . : Realtek PCIe GbE Family Controller
   Physical Address. . . . . . . . . : XX-XX-XX-XX-XX-XX
   DHCP Enabled. . . . . . . . . . . : Yes
   Autoconfiguration Enabled . . . . : Yes
   Autoconfiguration IPv4 Address. . : 169.254.250.216
   Subnet Mask . . . . . . . . . . . : 255.255.0.0
   Default Gateway . . . . . . . . . :

Ethernet adapter VirtualBox Host-Only Network:

   Connection-specific DNS Suffix  . :
   Description . . . . . . . . . . . : VirtualBox Host-Only Ethernet Adapter
   Physical Address. . . . . . . . . : XX-XX-XX-XX-XX-XX
   DHCP Enabled. . . . . . . . . . . : No
   Autoconfiguration Enabled . . . . : Yes
   IPv4 Address. . . . . . . . . . . : 192.168.56.1(Preferred)
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
   Default Gateway . . . . . . . . . :
```

### Analiz

| Arayüz | IP | Durum |
|:-------|:---|:------|
| Wi-Fi (ana) | `192.168.0.20/24` | ✅ DHCP, DNS=Google |
| Ethernet | `169.254.250.216/16` | ⚠️ DHCP hatası, APIPA |
| VirtualBox | `192.168.56.1/24` | ✅ Host-only |

### Öğrenilenler
- Ethernet kablosu takılı değil (APIPA atamış)
- DNS Google DNS kullanıyor (8.8.8.8)
- VirtualBox ağı var → Kali sanal makine veya WSL2

---

## netstat -an

```
Active Connections

  Proto  Local Address          Foreign Address        State
  TCP    0.0.0.0:135            0.0.0.0:0              LISTENING
  TCP    0.0.0.0:445            0.0.0.0:0              LISTENING
  TCP    0.0.0.0:1234           0.0.0.0:0              LISTENING
  TCP    0.0.0.0:5040           0.0.0.0:0              LISTENING
  TCP    0.0.0.0:7680           0.0.0.0:0              LISTENING
  TCP    0.0.0.0:49664          0.0.0.0:0              LISTENING
  TCP    0.0.0.0:49665          0.0.0.0:0              LISTENING
  TCP    0.0.0.0:49666          0.0.0.0:0              LISTENING
  TCP    0.0.0.0:49667          0.0.0.0:0              LISTENING
  TCP    0.0.0.0:49668          0.0.0.0:0              LISTENING
  TCP    0.0.0.0:49669          0.0.0.0:0              LISTENING
  TCP    192.168.0.20:139       0.0.0.0:0              LISTENING
  TCP    192.168.0.20:54480     34.107.221.82:443      ESTABLISHED
  TCP    192.168.0.20:54482     34.107.221.82:443      ESTABLISHED
  TCP    192.168.0.20:54485     140.82.112.25:443      ESTABLISHED
  TCP    192.168.0.20:54488     185.199.111.154:443    ESTABLISHED
  TCP    192.168.0.20:54491     185.199.110.133:443    ESTABLISHED
  TCP    192.168.0.20:54493     13.107.42.14:443       ESTABLISHED
  TCP    192.168.0.20:54495     52.178.46.100:443      ESTABLISHED
  TCP    192.168.0.20:54497     40.126.32.21:443       ESTABLISHED
  TCP    192.168.0.20:54499     13.91.93.253:443       ESTABLISHED
  TCP    192.168.0.20:54502     185.199.111.154:443    ESTABLISHED
  TCP    192.168.0.20:54505     185.199.110.133:443    ESTABLISHED
  TCP    192.168.0.20:54511     52.114.71.13:443       ESTABLISHED
  TCP    192.168.0.20:54515     34.120.76.157:443      ESTABLISHED
  TCP    127.0.0.1:6942         0.0.0.0:0              LISTENING
  UDP    0.0.0.0:5353           *:*                    LISTENING
  UDP    0.0.0.0:5355           *:*                    LISTENING
  ...
```

### Açık Portlar (LISTENING)

| Port | Servis | 
|:-----|:-------|
| 135 | RPC Endpoint Mapper |
| 139 | NetBIOS Session |
| 445 | SMB (Dosya paylaşımı) |
| 1234 | ✅ **Hermes Agent** |
| 5040 | Windows Sistemi |
| 7680 | Windows Update |
| 6942 | Localhost servis |

### Uzak Bağlantılar (ESTABLISHED)

| Hedef IP | Servis |
|:---------|:-------|
| 34.107.221.82:443 | Google/Cloud |
| 140.82.112.25:443 | GitHub |
| 185.199.111.154:443 | GitHub Pages |
| 13.107.42.14:443 | Microsoft |
| 52.178.46.100:443 | Azure |
| 40.126.32.21:443 | Microsoft |
| 52.114.71.13:443 | Teams/Skype |
| 34.120.76.157:443 | Google Cloud |

### Öğrenilenler
- Hermes port 1234'te çalışıyor ✅
- SMB (445) açık → dosya paylaşımı aktif
- GitHub, Microsoft, Google, Azure bağlantıları var
- Telegram, tarayıcı, VS Code muhtemelen açık
