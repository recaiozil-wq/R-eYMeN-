# -*- coding: utf-8 -*-
"""
memory_manager.py — ReYMeN kalıcı hafıza yöneticisi.

ReYMeN'teki MEMORY.md + USER.md sisteminin ReYMeN versiyonu.
Her oturum başında hafızayı yükler, gerektiğinde günceller.

Kullanım:
    >>> from reymen.hafiza.memory_manager import MemoryManager
    >>> mm = MemoryManager()
    >>> hafiza = mm.yukle()
    >>> mm.ekle("memory", "Kullanıcı kısa cevapları sever")
    >>> print(mm.ozet())
"""

import os
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

MEMORY_LIMIT_CHARS = 50000
USER_LIMIT_CHARS = 50000


class MemoryManager:
    """Kalıcı hafıza yöneticisi.

    MEMORY.md: Ajanın kalıcı notları (ortam, öğrenilen bilgiler).
    USER.md: Kullanıcı profili (tercihler, iletişim tarzı).
    """

    def __init__(self, memory_path: str = None, user_path: str = None):
        """Hafıza yöneticisini başlat.

        Args:
            memory_path: MEMORY.md tam yolu (None=varsayılan)
            user_path: USER.md tam yolu (None=varsayılan)
        """
        kok = Path(__file__).parent.resolve()
        self.memory_path = Path(memory_path) if memory_path else kok / "MEMORY.md"
        self.user_path = Path(user_path) if user_path else kok / "USER.md"

    def yukle(self) -> dict:
        """MEMORY.md ve USER.md'yi oku.

        Returns:
            {"memory": str, "user": str, "memory_limit": int, "user_limit": int}
        """
        return {
            "memory": self._oku(self.memory_path),
            "user": self._oku(self.user_path),
            "memory_limit": MEMORY_LIMIT_CHARS,
            "user_limit": USER_LIMIT_CHARS,
        }

    def kaydet(self, memory_icerik: str = None, user_icerik: str = None) -> bool:
        """Güncellenmiş hafızayı dosyaya yaz.

        Args:
            memory_icerik: MEMORY.md için yeni içerik (None=dokunma)
            user_icerik: USER.md için yeni içerik (None=dokunma)

        Returns:
            Başarılı mı?
        """
        try:
            if memory_icerik is not None:
                self._yaz(self.memory_path, memory_icerik[:MEMORY_LIMIT_CHARS])
            if user_icerik is not None:
                self._yaz(self.user_path, user_icerik[:USER_LIMIT_CHARS])
            return True
        except Exception as e:
            print(f"[MemoryManager] Kayıt hatası: {e}")
            return False

    def guncelle(self, hedef: str, anahtar: str, deger: str) -> bool:
        """Hafızada bir anahtarı güncelle.

        Args:
            hedef: "memory" veya "user"
            anahtar: Başlık (örn: "Kullanıcı Tercihleri")
            deger: Yeni değer

        Returns:
            Başarılı mı?
        """
        dosya = self.memory_path if hedef == "memory" else self.user_path
        icerik = self._oku(dosya)
        sinir = MEMORY_LIMIT_CHARS if hedef == "memory" else USER_LIMIT_CHARS

        # Anahtarı bul ve güncelle, yoksa ekle
        yeni = self._anahtar_guncelle(icerik, anahtar, deger)

        if len(yeni) > sinir:
            print(f"[MemoryManager] UYARI: {dosya.name} limit aşıldı ({len(yeni)}/{sinir})")
            yeni = yeni[:sinir]

        return self._yaz(dosya, yeni)

    def ekle(self, hedef: str, metin: str) -> bool:
        """Hafızaya yeni bilgi ekle (sona ekler).

        Args:
            hedef: "memory" veya "user"
            metin: Eklenecek metin

        Returns:
            Başarılı mı?
        """
        dosya = self.memory_path if hedef == "memory" else self.user_path
        icerik = self._oku(dosya)
        sinir = MEMORY_LIMIT_CHARS if hedef == "memory" else USER_LIMIT_CHARS

        yeni = icerik + f"\n- {metin}\n"

        if len(yeni) > sinir:
            print(f"[MemoryManager] UYARI: {dosya.name} limit aşıldı ({len(yeni)}/{sinir})")
            yeni = yeni[-sinir:]

        return self._yaz(dosya, yeni)

    def ozet(self) -> str:
        """Hafıza özeti: karakter sayısı, doluluk oranı."""
        m_icerik = self._oku(self.memory_path)
        u_icerik = self._oku(self.user_path)

        return (
            f"📝 MEMORY.md: {len(m_icerik):,}/{MEMORY_LIMIT_CHARS:,} karakter "
            f"(%{len(m_icerik)*100//MEMORY_LIMIT_CHARS})\n"
            f"👤 USER.md: {len(u_icerik):,}/{USER_LIMIT_CHARS:,} karakter "
            f"(%{len(u_icerik)*100//USER_LIMIT_CHARS})"
        )

    def _oku(self, dosya: Path) -> str:
        """Dosyayı oku, yoksa boş dön."""
        try:
            if dosya.exists():
                return dosya.read_text(encoding="utf-8")
        except Exception as _e:
            logger.warning("[MemoryManager] except Exception (L138): %s", Exception)
            pass
        return ""

    def _yaz(self, dosya: Path, icerik: str) -> bool:
        """Dosyaya yaz."""
        try:
            dosya.parent.mkdir(parents=True, exist_ok=True)
            dosya.write_text(icerik, encoding="utf-8")
            return True
        except Exception as e:
            print(f"[MemoryManager] Yazma hatası: {e}")
            return False

    def _anahtar_guncelle(self, icerik: str, anahtar: str, deger: str) -> str:
        """İçerikte bir başlık altındaki değeri güncelle."""
        satirlar = icerik.split("\n")
        yeni = []
        hedef_baslik = f"## {anahtar}"
        bulundu = False
        baslik_satiri = -1

        for i, satir in enumerate(satirlar):
            if satir.strip().startswith(f"## {anahtar}"):
                baslik_satiri = i
                bulundu = True
                yeni.append(satir)
            elif baslik_satiri >= 0 and i > baslik_satiri:
                # Başlıktan sonraki boş satır veya içerik
                if satir.strip().startswith("##"):
                    # Yeni başlık başladı, eski başlığı atla
                    yeni.append(satir)
                    baslik_satiri = -1
                elif not bulundu:
                    yeni.append(deger)
                    bulundu = True
                else:
                    # Eski içeriği atla
                    continue
            else:
                yeni.append(satir)

        # Başlık hiç bulunamadıysa ekle
        if baslik_satiri == -1 and anahtar:
            yeni.append(f"\n## {anahtar}")
            yeni.append(deger)

        return "\n".join(yeni)


# Tekil nesne (singleton)
_singleton = None


def get_memory() -> MemoryManager:
    """Tekil MemoryManager örneğini döndür."""
    global _singleton
    if _singleton is None:
        _singleton = MemoryManager()
    return _singleton


def hafiza_yukle() -> dict:
    """Kısayol: hafızayı yükle."""
    return get_memory().yukle()


def hafiza_ekle(hedef: str, metin: str) -> bool:
    """Kısayol: hafızaya bilgi ekle."""
    return get_memory().ekle(hedef, metin)


def hafiza_guncelle(hedef: str, anahtar: str, deger: str) -> bool:
    """Kısayol: hafızada güncelle."""
    return get_memory().guncelle(hedef, anahtar, deger)


def hafiza_ozet() -> str:
    """Kısayol: hafıza özeti."""
    return get_memory().ozet()
