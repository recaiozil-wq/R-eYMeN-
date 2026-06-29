---
name: Tor Browser ac ve alanya hava durumu hak
description: Tor Browser açıldı ancak internet bağlantısı sorunu nedeniyle Alanya hava durumu bilgisi alınamadı. Lütfen internet bağlantınızı kontrol edip tekrar deneyin. Alternatif olarak, https://www.mgm.gov.tr sitesinden Alanya hava durumunu manuel olarak kontrol edebilirsiniz.
created: 2026-06-21
usage_count: 1
last_used: 2026-06-21
---


> **Kategori:** tor

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Tor Browser açıldı ancak internet bağlantısı sorunu nedeniyle Alanya hava durumu bilgisi alınamadı. Lütfen internet bağlantınızı kontrol edip tekrar deneyin. Alternatif olarak, https://www.mgm.gov.tr sitesinden Alanya hava durumunu manuel olarak kontrol edebilirsiniz. |
| **Nerede?** | tor/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Tor Browser ac ve alanya hava durumu hak

Tor Browser açıldı ancak internet bağlantısı sorunu nedeniyle Alanya hava durumu bilgisi alınamadı. Lütfen internet bağlantınızı kontrol edip tekrar deneyin. Alternatif olarak, https://www.mgm.gov.tr sitesinden Alanya hava durumunu manuel olarak kontrol edebilirsiniz.

## Adimlar

KOMUT_CALISTIR: "tor-browser & sleep 5 && echo 'Tor Browser açıldı'"
WEB_ARA: "Alanya hava durumu 2025"
TARAYICI_AC: "https://www.mgm.gov.tr/tahmin/il-ve-ilceler.aspx?il=Antalya&ilce=Alanya"
PYTHON_CALISTIR: "import urllib.request, json; print('Deneme')"
KOMUT_CALISTIR: "curl -s 'wttr.in/Alanya?format=%C+%t'"
PYTHON_CALISTIR: """
import urllib.request
import json

try:
    url = 'https://wttr.in/Alanya?format=j1'
    req = urllib.request.urlopen(url, timeout=10)
    data = json.loads(req.read().decode())
    current = data['current_condition'][0]
    temp = current['temp_C']
    desc = current['weatherDesc'][0]['value']
    humidity = current['humidity']
    wind = current['windspeedKmph']
    print(f'Alanya Hava Durumu:')
    print(f'Sıcaklık: {temp}°C')
    print(f'Durum: {desc}')
    print(f'Nem: {humidity}%')
    print(f'Rüzgar: {wind} km/s')
except Exception as e:
    print(f'Hata: {e}')
"""
KOMUT_CALISTIR: "pkill -f tor-browser 2>/dev/null; echo 'Tor Browser kapatıldı'"
