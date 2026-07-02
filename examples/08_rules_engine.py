#!/usr/bin/env python3
"""Ornek 8: Kural Motoru (Rules Engine) — izin/engel/uyari kurallari."""

try:
    from reymen.sistem.kurallar import RulesEngine, KATEGORILER, KURAL_TIPLERI
    import tempfile
    import os

    # Gecici kural dosyasi ile calis
    gecici_dizin = tempfile.mkdtemp()
    gecici_kural_yolu = os.path.join(gecici_dizin, "test_kurallar.yaml")

    engine = RulesEngine(rules_file=gecici_kural_yolu)

    print(f"=== Kural Motoru (RulesEngine) ===")
    print(f"Varsayilan kural sayisi: {engine.kural_sayisi}")
    print(f"Kategoriler: {', '.join(sorted(KATEGORILER))}")
    print(f"Tipler: {', '.join(sorted(KURAL_TIPLERI))}")

    # 1. Yeni kural ekle
    print("\n1. Yeni kural ekleniyor...")
    basarili, mesaj = engine.kural_ekle(
        kategori="dosya_erisim",
        tip="engel",
        desen="**.secret*",
        sebep="Gizli dosyalara erisim engeli",
        kural_id="test-gizli-dosya",
    )
    print(f"  {'✅' if basarili else '❌'} {mesaj}")

    # 2. Kontrol: engellenmeli
    print("\n2. Kontrol: '.env' dosyasi...")
    sonuc = engine.kontrol("dosya_erisim", "/proje/.env")
    print(f"  Izin: {sonuc['izin']} | Sebep: {sonuc['sebep']}")

    # 3. Kontrol: izin verilmeli
    print("\n3. Kontrol: guvenli dosya (README.md)...")
    sonuc2 = engine.kontrol("dosya_erisim", "/proje/README.md")
    print(f"  Izin: {sonuc2['izin']} | Sebep: {sonuc2['sebep']}")

    # 4. Kurallari listele
    print(f"\n4. Tum kurallar ({len(engine._rules)}):")
    for k in engine._rules:
        aktif = "✅" if k.get("aktif") else "❌"
        print(f"  {aktif} [{k['id']}] {k['kategori']}/{k['tip']} -> {k['desen']}")

    # 5. Toplu kontrol
    print("\n5. Toplu kontrol (3 aksiyon)...")
    kontroller = [
        {"kategori": "dosya_erisim", "hedef": "/etc/passwd"},
        {"kategori": "komut", "hedef": "rm -rf /"},
        {"kategori": "ag", "hedef": "api.deepseek.com"},
    ]
    toplu = engine.toplu_kontrol(kontroller)
    for i, tc in enumerate(toplu):
        ikon = "✅" if tc["izin"] else "❌"
        print(f"  {ikon} {kontroller[i]['hedef']}: {tc['sebep'][:50]}")

    # 6. Kural sil
    print("\n6. Kural siliniyor...")
    basarili3, mesaj3 = engine.kural_sil("test-gizli-dosya")
    print(f"  {'✅' if basarili3 else '❌'} {mesaj3}")

    # Temizlik
    import shutil
    shutil.rmtree(gecici_dizin, ignore_errors=True)

except ImportError as e:
    print(f"[ATLA] Modul bulunamadi: {e}")
except Exception as e:
    print(f"[HATA] {type(e).__name__}: {e}")
