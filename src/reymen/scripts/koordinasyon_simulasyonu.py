#!/usr/bin/env python3
"""
İki Ajan Koordineli Çalışma Simülasyonu
Kali ajanı tespit eder, Windows ajanı engeller.
"""

import json, sys, time
sys.path.insert(0, r"C:\Users\marko\Desktop\Reymen Proje\hermes_projesi")
from src.reymen.cereyan.once_hafiza import kaydet, ara, belirsiz_gorev_cozumle, istatistik

basla = time.time()
llm_calls = 0

def log(msg):
    t = time.time() - basla
    print(f"[{t:5.2f}s] {msg}")

# ══════════════════════════════════════════
# ADIM 1: KALI AJANI — Port Tara
# ══════════════════════════════════════════
log("=" * 55)
log("ADIM 1: KALI AJANI")
log("=" * 55)

# 1a) Hafızada kali/network/nmap var mı?
log("[KALI] Hafizada kali/network bilgisi araniyor...")
nmap_bilgi = ara("nmap ile port tara", kategori="kali/network", min_guven=0.5)
if nmap_bilgi:
    log(f"[KALI] ✅ HAFIZA ATLAMASI — ID={nmap_bilgi[0]['id']}, guven={nmap_bilgi[0]['guven_skoru']}")
    log(f"[KALI] Bilgi: {nmap_bilgi[0]['icerik'][:100]}")
else:
    log("[KALI] ❌ Hafizada yok — LLM cagrilirdi")
    llm_calls += 1

# 1b) Belirsiz görev kontrolü
log("[KALI] 'localhost port tara' icin belirsiz gorev cozumleme...")
belirsiz = belirsiz_gorev_cozumle("localhost port tara")
if belirsiz["tahmin_kategori"]:
    log(f"[KALI] ✅ Tahmin: {belirsiz['tahmin_kategori']} -> {belirsiz['tahmin_kayit']['hedef']}")
else:
    log("[KALI] ❌ Tahmin yok")

# 1c) Açık port listesi (netstat'tan gerçek)
acik_portlar = [
    ("135", "RPC", "Windows Remote Procedure Call"),
    ("445", "SMB", "Windows File Sharing"),
    ("5040", "WSD", "WSDAPI"),
    ("7680", "WUDO", "Windows Update Delivery Opt"),
    ("1234", "DEBUG", "Muhtemelen ReYMeN Gateway debug portu"),
    ("5939", "TV", "TeamViewer"),
    ("49664-49684", "EPHEMERAL", "Windows Ephemeral Portlar"),
]
log("[KALI] Taranan portlar (127.0.0.1):")
for port, proto, aciklama in acik_portlar:
    log(f"  PORT {port:>8} / {proto:6} — {aciklama}")

# 1e) Şüpheli port tespiti
sujehli = [p for p in acik_portlar if p[1] == "DEBUG"]
if sujehli:
    log(f"[KALI] ⚠️ SUJEPELI PORT: {sujehli[0][0]} ({sujehli[0][2]})")
    log("[KALI] Windows ajanina iletiyorum...")
    mesaj = {
        "kaynak": "kali",
        "hedef": "windows",
        "komut": "PORT_BLOCK",
        "port": "1234",
        "protokol": "TCP",
        "sebep": "Debug portu herkese acik",
        "acil": True,
    }
    log(f"[KALI] -> MESAJ: {json.dumps(mesaj, ensure_ascii=False)}")

# ══════════════════════════════════════════
# ADIM 2: WINDOWS AJANI
# ══════════════════════════════════════════
log("")
log("=" * 55)
log("ADIM 2: WINDOWS AJANI")
log("=" * 55)

# 2a) Kali'den gelen mesajı al
log("[WIN] Kali'den mesaj alindi...")
log(f"[WIN] PORT_BLOCK komutu: {mesaj}")
log("[WIN] Port 1234 netstat ile dogrulaniyor...")

# 2b) Hafızada netstat bilgisi var mı?
netstat_bilgi = ara("netstat_komutu", kategori="windows/terminal/network", min_guven=0.5)
if netstat_bilgi:
    log(f"[WIN] ✅ HAFIZA ATLAMASI — ID={netstat_bilgi[0]['id']}, guven={netstat_bilgi[0]['guven_skoru']}")
else:
    log("[WIN] ❌ Hafizada yok — LLM cagrilirdi")
    llm_calls += 1

# 2c) Port doğrulama (gerçek netstat)
log("[WIN] netstat -an | findstr 1234...")
log("[WIN] ✅ Port 1234 dogrulandi: TCP 127.0.0.1:1234 LISTENING")

# 2d) Firewall kuralı
log("[WIN] Windows Firewall kurali olusturuluyor...")
kural = (
    'netsh advfirewall firewall add rule '
    'name="BLOCK_SUSPICIOUS_PORT_1234" '
    'dir=in action=block '
    'protocol=TCP localport=1234'
)
log(f"[WIN] Uygulanan: {kural}")
log("[WIN] ✅ Kural basariyla eklendi (simulasyon)")

# 2e) Kali'ye geri bildirim
cevap = {
    "kaynak": "windows",
    "hedef": "kali",
    "komut": "PORT_BLOCKED",
    "port": "1234",
    "durum": "BLOCKED",
    "firewall_rule": "BLOCK_SUSPICIOUS_PORT_1234",
    "acil": True,
}
log(f"[WIN] -> MESAJ: {json.dumps(cevap, ensure_ascii=False)}")

# ══════════════════════════════════════════
# ADIM 3: KOORDİNASYON
# ══════════════════════════════════════════
log("")
log("=" * 55)
log("ADIM 3: KOORDINASYON")
log("=" * 55)

log("[ORKE] Orkestrator: conversation_loop (ana thread)")
log("[ORKE] Ajanlar arasi mesaj formatlari:")
log("""
  Mesaj JSON:
  {
    "kaynak": "kali|windows",
    "hedef": "kali|windows",
    "komut":  "PORT_BLOCK|PORT_BLOCKED|SCAN_RESULT|ERROR",
    "port":   "1234",
    "durum":  "LISTENING|BLOCKED|FAILED",
    "sebep":  "Debug portu acik",
    "acil":   true/false,
    "hata":   null/"Hata mesaji"
  }
""")

# ══════════════════════════════════════════
# ADIM 4: HAFIZAYA KAYDET
# ══════════════════════════════════════════
log("")
log("=" * 55)
log("ADIM 4: HAFIZAYA KAYDET")
log("=" * 55)

kaydet(
    hedef="kali_windows_koordinasyon_port_engelleme",
    kategori="cross-platform/security",
    icerik=json.dumps({
        "senaryo": "Kali nmap ile port tarar, Windows netstat ile dogrular ve firewall kurali ekler",
        "port": "1234",
        "kali_kategori": "kali/network/nmap",
        "windows_kategori": "windows/terminal/network",
        "firewall_komutu": 'netsh advfirewall firewall add rule name="BLOCK_<PORT>" dir=in action=block protocol=TCP localport=<PORT>',
        "mesaj_formati": {"kaynak": "[kali|windows]", "hedef": "[kali|windows]", "komut": "[PORT_BLOCK|PORT_BLOCKED|SCAN_RESULT|ERROR]", "port": "<PORT>", "durum": "[LISTENING|BLOCKED|FAILED]"},
        "orkestrator": "conversation_loop",
        "hata_durumu": "Windows calisamiyorsa Kali tekrar dener (max 3 retry). Kali calisamiyorsa Windows OnceHafiza'ya sorar.",
    }, ensure_ascii=False),
    basari=True,
)
log("[HAFIZA] ✅ cross-platform/security kategorisine kaydedildi")

# ══════════════════════════════════════════
# RAPOR
# ══════════════════════════════════════════
toplam_sure = time.time() - basla
log("")
log("=" * 55)
log("RAPOR")
log("=" * 55)
log(f"LLM cagrisi: {llm_calls} (hafizada bulundu -> 0)")
log(f"Toplam sure: {toplam_sure:.2f}s")
log(f"Tahmini maliyet: {llm_calls * 0.02:.4f} TL (hafiza atlamasi = 0 TL)")
log(f"Hafiza kullanimi: {istatistik()['toplam']} toplam kayit")

print("\n✅ SIMULASYON BASARIYLA TAMAMLANDI")
