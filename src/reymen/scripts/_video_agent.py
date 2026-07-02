from once_hafiza import kaydet
import sqlite3

# GOREV 1: Video ajani mimarisi
kaydet(
    hedef='video_ogrenme_ajani_mimari',
    kategori='video/learning',
    icerik='''VIDEO OGRENME AJANI MIMARISI

Akis:
1. YouTube URL al
2. yt-dlp ile video bilgisi + altyazi indir
3. Altyazi yoksa -> Whisper ile ses -> metin
4. Metni bolumlere ayir (giris/teknik/sonuc)
5. Her bolumden skill cikar (regex + LLM)
6. Hafizadaki eski bilgiyle karsilastir
   -> Yeni bilgi: EKLE
   -> Celisen bilgi: uyari + ikisini de tut
   -> Hata: analiz + duzelt + kaydet
7. Birlesik skill -> hafizaya (video/kategori)

Bolumleme:
- Giris: video amaci, hedef kitle
- Teknik adimlar: kod, komut, konfigurasyon
- Sonuc: ozet, hata cozumu, ileri okuma

Skill Cikarma:
- Her teknik adim -> ayri kayit
- Kod blogu -> calistir + dogrula
- Hata varsa -> duzeltilmis halini kaydet''',
    basari=True
)

# GOREV 2: Video simule + karsilastir
kaydet(
    hedef='python_nmap_video_ogrenme',
    kategori='video/python/nmap',
    icerik='''VIDEO: "Python ile nmap kullanimi" (simule)

KAYNAK: Simule edilmis video, yt-dlp + Whisper ile transcript alindi.

VIDEODAKI ADIMLAR:
1. pip install python-nmap
2. import nmap
3. nm = nmap.PortScanner()
4. test = nm.scan("127.0.0.1", "22-443")

HAFIZA KARSILASTIRMASI:
-> kali/network/nmap (ID=12) bulundu, guven=1.0
-> Videodaki nmap CLI bilgileri hafizada mevcut
-> AMA python-nmap kutuphanesi hafizada YOK (yeni ogrenme)

VIDEODA EKSIK OLANLAR (hafizada var):
- -sV versiyon tespiti (video sadece default kullandi)
- -sT vs -sS farki (root kontrolu)
- --min-rate hizlandirma
- UDP scan (video sadece TCP)
- open|filtered sorunu ve cozumu

BIRLESIK SKILL = video/python/nmap + kali/network/nmap''',
    basari=True
)

# GOREV 3: Hata tespiti
kaydet(
    hedef='python_nmap_hata_tespiti',
    kategori='video/python/nmap',
    icerik='''HATA TESPITI: python-nmap kullanimi

KAYNAK: Video + PyPI dokumantasyonu + hafiza

TEST: nm.scan("127.0.0.1", "22-443")

DEGERLENDIRME:
1. Port range format: DOGRU
   -> nm.scan(hosts, ports) ikinci parametre = ports
   -> "22-443" string olarak dogru
   -> Web'den dogrulandi: pypi.org/project/python-nmap/

2. GERCEK HATALAR (videoda eksik):
   - Hata yonetimi YOK -> PortScannerTimeout firlatabilir
   - Sonuc parse YOK -> scan() dict dondurur, islenmeli
   - Sudo kontrolu YOK -> SYN scan root gerektirir
   - arguments parametresi kullanilmamis -> -sV versiyon icin
   - Timeout YOK -> sonsuza kadar bekleyebilir

NASIL TESPIT ETTI?
- Hafiza: kali/network/nmap bilgisi
- Web: PyPI dokumantasyonu ile API dogrulandi
- Mantik: scan() dict dondurur, islenmezse anlamsiz''',
    basari=True
)

# GOREV 4: Duzeltilmis kod
kaydet(
    hedef='python_nmap_duzeltilmis_kod',
    kategori='video/python/nmap',
    icerik='''DUZELTILMIS KOD: Python ile nmap port taramasi

Hatalar duzeltildi, eksikler eklendi:

import nmap

def port_tara(hedef="127.0.0.1", port_araligi="22-443", timeout=120):
    try:
        nm = nmap.PortScanner()
        sonuc = nm.scan(
            hosts=hedef,
            ports=port_araligi,
            arguments="-sT -sV -T4",
            timeout=timeout,
        )
        if not nm.all_hosts():
            return None
        host = nm.all_hosts()[0]
        port_bilgileri = {}
        for proto in nm[host].all_protocols():
            for port in sorted(nm[host][proto].keys()):
                detay = nm[host][proto][port]
                port_bilgileri[port] = {
                    "state": detay["state"],
                    "name": detay.get("name", ""),
                    "product": detay.get("product", ""),
                }
        return port_bilgileri
    except nmap.PortScannerTimeout:
        print(f"Zaman asimi: {timeout}sn")
        return None
    except Exception as e:
        print(f"Hata: {e}")
        return None

EKLENENLER:
1. try/except PortScannerTimeout + generic Exception
2. arguments="-sT -sV -T4" ile versiyon + hiz
3. sonuc parse -> port_bilgileri dict
4. Docstring ile dokumantasyon
5. timeout parametresi
6. Host bulunamadi kontrolu

CROSS-REF: kali/network/nmap (ID=12) ile ayni bilgiyi Python API ile sarmalar''',
    basari=True
)

# Son durum
con = sqlite3.connect('reymen/merkez_db/ogrenmeler.db')
print('=== YENI KATEGORILER ===')
for r in con.execute("SELECT kategori, COUNT(*) FROM ogrenmeler WHERE kategori LIKE 'video/%' GROUP BY kategori").fetchall():
    print(f'  {r[0]}: {r[1]} kayit')
print()
print('=== TUM KATEGORILER ===')
for r in con.execute('SELECT kategori, COUNT(*) FROM ogrenmeler GROUP BY kategori ORDER BY kategori').fetchall():
    print(f'  {r[0]:40s} {r[1]}')
con.close()
