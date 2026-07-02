"""
WiFi ağındaki cihazları tara — IP + MAC adreslerini bul.

SelfHeal test örneği:
1. nmap ile subnet tara
2. ARP tablosunu oku
3. Sonuçları tablo olarak göster
4. Hata olursa → SelfHeal otomatik düzeltir
"""

import subprocess, re, sys, json
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

# ── 1. Ağ arayüzünü bul ──────────────────────────────────────

def aktif_interface_bul() -> str:
    """WiFi arayüzünün IP'sini bul — dynamic ARP entry'si olan tercih edilir."""
    try:
        # Önce arp -a ile dynamic entry'si olan interface'i bul
        arp_r = subprocess.run(["arp", "-a"], capture_output=True, text=False, timeout=15)
        arp_cikti = arp_r.stdout.decode("utf-8", errors="replace")

        # Her interface bloğunu ayır
        bloklar = arp_cikti.split("Interface:")
        for blok in bloklar[1:]:  # ilk blok header
            ilk_satir = blok.splitlines()[0] if blok.splitlines() else ""
            m_if = re.search(r'(\d+\.\d+\.\d+\.\d+)', ilk_satir)
            if not m_if:
                continue
            if_ip = m_if.group(1)
            # Bu blokta dynamic entry var mı?
            if "dynamic" in blok:
                return if_ip

        # Fallback: ipconfig
        r = subprocess.run(["ipconfig"], capture_output=True, text=False, timeout=15)
        cikti = r.stdout.decode("utf-8", errors="replace")
        for line in cikti.splitlines():
            m = re.search(r'IPv4[^:]*:\s*(\d+\.\d+\.\d+\.\d+)', line)
            if m:
                ip = m.group(1)
                if ip.startswith(("192.168.", "10.")):
                    return ip
    except Exception as e:
        print(f"[HATA] aktif_interface_bul: {e}")
    return ""


def subnet_bul(ip: str) -> str:
    """IP'den /24 subnet hesapla."""
    parts = ip.split(".")
    parts[-1] = "0"
    return ".".join(parts) + "/24"


# ── 2. ARP tablosu ──────────────────────────────────────────

def arp_tara() -> list[dict]:
    """arp -a komutu ile cihazları bul."""
    cihazlar = []
    try:
        r = subprocess.run(["arp", "-a"], capture_output=True, text=False, timeout=15)
        cikti = r.stdout.decode("utf-8", errors="replace")
        for line in cikti.splitlines():
            m = re.search(
                r'(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F\-]{17})\s+(dynamic|static)',
                line
            )
            if m:
                ip = m.group(1)
                mac = m.group(2).replace("-", ":").lower()
                tur = m.group(3)
                # Multicast/broadcast filtrele
                if not ip.startswith(("224.", "239.", "255.")):
                    cihazlar.append({"ip": ip, "mac": mac, "turu": tur})
    except Exception as e:
        print(f"[HATA] arp -a: {e}")
    return cihazlar


# ── 3. Nmap taraması ────────────────────────────────────────

def nmap_tara(subnet: str) -> list[dict]:
    """nmap -sn ile canlı cihazları tara."""
    cihazlar = []
    try:
        r = subprocess.run(
            ["nmap", "-sn", subnet],
            capture_output=True, text=False, timeout=60
        )
        cikti = r.stdout.decode("utf-8", errors="replace")
        ip_bulundu = None
        for line in cikti.splitlines():
            m_ip = re.search(r'Nmap scan report for (\d+\.\d+\.\d+\.\d+)', line)
            if m_ip:
                ip_bulundu = m_ip.group(1)
                continue
            m_mac = re.search(r'MAC Address:\s+([0-9A-Fa-f:]{17})', line)
            if m_mac and ip_bulundu:
                mac = m_mac.group(1).lower()
                # Uretici bilgisi de var: MAC Address: XX:XX:XX:XX:XX:XX (Intel)
                uretici = ""
                u_m = re.search(r'MAC Address:\s+[0-9A-Fa-f:]{17}\s+\((.+)\)', line)
                if u_m:
                    uretici = u_m.group(1)
                if not ip_bulundu.startswith(("224.", "239.", "255.")):
                    cihazlar.append({
                        "ip": ip_bulundu,
                        "mac": mac,
                        "uretici": uretici,
                        "turu": "dynamic"
                    })
                ip_bulundu = None
    except subprocess.TimeoutExpired:
        print("[UYARI] nmap zaman aşımı (60s)")
    except FileNotFoundError:
        print("[UYARI] nmap bulunamadı, sadece ARP kullanılacak")
    except Exception as e:
        print(f"[HATA] nmap: {e}")
    return cihazlar


# ── 4. Ana ───────────────────────────────────────────────────

def main():
    print("╔══════════════════════════════════════════════╗")
    print("║    WiFi Cihaz Taraması (IP + MAC)          ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    # Ağ bilgisi
    ip = aktif_interface_bul()
    if not ip:
        print("❌ Aktif ağ arayüzü bulunamadı.")
        return

    subnet = subnet_bul(ip)
    print(f"📡 Arayüz IP: {ip}")
    print(f"🌐 Subnet:    {subnet}")
    print()

    # ARP tablosu
    print("📋 ARP tablosu taranıyor...")
    arp_cihazlar = arp_tara()
    print(f"   ARP'de {len(arp_cihazlar)} cihaz bulundu")

    # Nmap taraması
    print("🔍 Nmap ile canlı cihaz taranıyor...")
    nmap_cihazlar = nmap_tara(subnet)
    print(f"   Nmap'te {len(nmap_cihazlar)} cihaz bulundu")

    # Birleştir (nmap öncelikli)
    gorulen_ip = set()
    tum_cihazlar = []

    for c in nmap_cihazlar:
        gorulen_ip.add(c["ip"])
        tum_cihazlar.append(c)
    for c in arp_cihazlar:
        if c["ip"] not in gorulen_ip:
            gorulen_ip.add(c["ip"])
            tum_cihazlar.append(c)

    # Sırala
    tum_cihazlar.sort(key=lambda x: [int(p) for p in x["ip"].split(".")])

    # Tablo göster
    print()
    print("┌─────────────────────┬────────────────────┬──────────────┐")
    print("│ IP                  │ MAC                │ Üretici      │")
    print("├─────────────────────┼────────────────────┼──────────────┤")

    for c in tum_cihazlar:
        ip_str = c["ip"].ljust(19)
        mac_str = c["mac"].ljust(18)
        uretici = c.get("uretici", c.get("turu", ""))[:12].ljust(12)
        print(f"│ {ip_str}│ {mac_str}│ {uretici}│")

    print("└─────────────────────┴────────────────────┴──────────────┘")
    print(f"\n📊 Toplam: {len(tum_cihazlar)} cihaz")

    # JSON çıktı (self_heal için)
    cikti = {
        "zaman": datetime.now().isoformat(),
        "interface_ip": ip,
        "subnet": subnet,
        "cihaz_sayisi": len(tum_cihazlar),
        "cihazlar": tum_cihazlar
    }
    with open("wifi_cihazlari_sonuc.json", "w", encoding="utf-8") as f:
        json.dump(cikti, f, indent=2, ensure_ascii=False)
    print(f"\n💾 JSON kaydedildi: wifi_cihazlari_sonuc.json")


if __name__ == "__main__":
    main()
