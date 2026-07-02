#!/usr/bin/env python3
"""Ornek 4: FTS5 Session Search — mesajlari kaydet ve tam metin ara."""

try:
    from reymen.cereyan.session_search import SessionSearch

    # 1. Arama motorunu baslat (test icin gecici db)
    import tempfile
    import os
    gecici_db = os.path.join(tempfile.gettempdir(), "reymen_test_fts.db")
    searcher = SessionSearch(db_yolo=gecici_db)

    # 2. Ornek mesajlari kaydet
    searcher.save("sohbet-1", "Merhaba, bugun hava cok guzel!", "user")
    searcher.save("sohbet-1", "Evet, disari cikip yuruyus yapabiliriz.", "assistant")
    searcher.save("sohbet-1", "Python ile yapay zeka ogreniyorum.", "user")
    searcher.save("sohbet-2", "ReYMeN projesinde FTS5 arama kullaniliyor.", "user")

    # 3. Arama yap
    sonuclar = searcher.search("yapay zeka")
    print(f"Arama: 'yapay zeka' -> {len(sonuclar)} sonuc")
    for s in sonuclar:
        print(f"  [{s['session_id']}] ({s['role']}) {s['message'][:60]}...")

    # 4. Session'a ozel arama
    sonuclar2 = searcher.search("hava", session_id="sohbet-1")
    print(f"\nSession 'sohbet-1' icin 'hava' -> {len(sonuclar2)} sonuc")
    for s in sonuclar2:
        print(f"  ({s['role']}) {s['message'][:60]}...")

    # 5. Istatistik
    istatistik = searcher.istatistik()
    print(f"\nIstatistik: {istatistik['toplam_mesaj']} mesaj, "
          f"{istatistik['toplam_session']} session")

    # Temizlik (opsiyonel)
    os.remove(gecici_db)

except ImportError as e:
    print(f"[ATLA] Modul bulunamadi: {e}")
except Exception as e:
    print(f"[HATA] {type(e).__name__}: {e}")
