# -*- coding: utf-8 -*-
"""web_search_tool.py — WEB_ARA tool implementasyonu.

Bu dosya, web_search_engine.py'deki SearchDispatcher'a yönlendirme yapar.
Geriye uyumluluk için korunuyor (motor.py tarafından _plugin_moduller_yukle()
ile yüklenir). Tüm arama mantığı web_search_engine.py'dedir.

Kullanim:
    from reymen.arac.web_search_tool import web_ara, web_arama_kaydet
    sonuc = web_ara("dolar kuru")
"""

import logging
from reymen.arac.web_search_engine import web_arama as _web_arama, _get_registry

log = logging.getLogger(__name__)


def web_ara(sorgu: str, max_sonuc: int = 5) -> str:
    """Dis dunyada arama yap. API key gerekmez.

    Args:
        sorgu: Arama sorgusu.
        max_sonuc: Maks sonuc sayisi.

    Returns:
        String: "[1] Baslik | url | ozet" formatinda sonuclar
        veya "Sonuc bulunamadi." mesaji.
    """
    return _web_arama(sorgu, backend="auto", max_sonuc=max_sonuc)


def web_arama_kaydet(motor) -> None:
    """WEB_ARA tool'unu motor'a kaydet.

    Cagri:
        motor._plugin_arac_kaydet("WEB_ARA", web_ara, "Web'de ara")
    """
    motor._plugin_arac_kaydet(
        "WEB_ARA", web_ara,
        "Web aramasi yapar (coklu back-end, auto-detect). "
        "Kullanim: WEB_ARA(sorgu=\"...\")."
    )


def motor_kaydet(motor) -> None:
    """Motor tarafindan otomatik cagrilir. WEB_ARA tool'unu kaydeder."""
    web_arama_kaydet(motor)


if __name__ == "__main__":
    # Test
    import sys
    sonuc = web_ara(" ".join(sys.argv[1:]) if len(sys.argv) > 1 else "test")
    print(sonuc)
