#!/usr/bin/env python3
"""Ornek 5: Sub-Agent Delegasyonu — gorevleri paralel alt-ajanlara devret."""

try:
    import json
    from reymen.tools.delegate_task_tool import delegate_task

    # Alt ajanlara dagitilacak gorev listesi
    gorevler = json.dumps([
        {"gorev": "2+2 kac eder? Kisa cevap ver.", "baglam": "matematik"},
        {"gorev": "Turkive'nin baskenti neresidir?", "baglam": "cografya"},
        {"gorev": "Python'da 'merhaba dunya' yazdiran kod yaz.", "baglam": "programlama"},
    ])

    print("=== Delegasyon Basliyor ===")
    print(f"Gorev sayisi: 3")
    print(f"Paralel: 2, Timeout: 30s, Max adim: 3\n")

    sonuc = delegate_task(
        gorev_tanimlari=gorevler,
        baglam_genel="Kisa ve oz cevap ver. Turkce konus.",
        max_paralel=2,
        timeout=30,
        max_adim=3,
    )

    print(sonuc)

except ImportError as e:
    print(f"[ATLA] Modul bulunamadi: {e}")
    print("(Bu ornek LLM erisimi gerektirir, bagimsiz calismayabilir)")
except Exception as e:
    print(f"[HATA] {type(e).__name__}: {e}")
