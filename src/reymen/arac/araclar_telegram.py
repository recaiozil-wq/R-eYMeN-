# -*- coding: utf-8 -*-
"""
araclar_telegram.py — Telegram araclari.

Telegram botu uzerinden mesaj gonderme, okuma, dosya gonderme
ve baglanti testi islemlerini saglayan sinif.

Kurulum:
    1. @BotFather ile bot olustur -> token al.
    2. Bota mesaj at -> https://api.telegram.org/bot<TOKEN>/getUpdates
    3. JSON icinden chat_id'ini bul.
    4. Token ve chat_id'i TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID olarak ayarla.
"""

import os
import json
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TelegramTools:
    """Telegram botu icin mesajlasma ve dosya transfer araclari.

    Ornek kullanim:
        bot = TelegramTools(token="123:ABC", chat_id="456")
        bot.mesaj_gonder(chat_id="456", mesaj="Merhaba Dunya")
        bot.ping()
    """

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        """TelegramTools sinifini baslat.

        Args:
            token: Telegram bot token. None ise TELEGRAM_BOT_TOKEN env'den alinir.
            chat_id: Varsayilan chat ID. None ise TELEGRAM_CHAT_ID env'den alinir.
        """
        self._token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self._chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")
        self._base_url = f"https://api.telegram.org/bot{self._token}"
        self._son_mesaj_id = 0
        self._timeout = 20
        logger.debug("TelegramTools baslatildi. Token var: %s", bool(self._token))

    def _api_istek(self, method: str, data: dict) -> dict:
        """Telegram API'sine istek gonder.

        Args:
            method: API metodu (sendMessage, getUpdates, vb.)
            data: Gonderilecek parametreler

        Returns:
            API yaniti sozluk olarak

        Raises:
            RuntimeError: Token ayarli degilse
        """
        if not self._token or "BURAYA" in self._token:
            raise RuntimeError("[TelegramTools] Token ayarli degil. TELEGRAM_BOT_TOKEN env'ini kontrol et.")

        try:
            import requests
            url = f"{self._base_url}/{method}"
            r = requests.post(url, data=data, timeout=self._timeout)
            r.raise_for_status()
            yanit = r.json()
            if not yanit.get("ok"):
                raise RuntimeError(f"Telegram API hatasi: {yanit.get('description', 'bilinmiyor')}")
            return yanit
        except ImportError:
            raise RuntimeError("[TelegramTools] requests kutuphanesi gerekli. pip install requests")
        except Exception as _e:
            _en = type(_e).__name__
            if "Timeout" in _en:
                raise RuntimeError(f"[TelegramTools] Zaman asimi: {method}")
            if "ConnectionError" in _en:
                raise RuntimeError(f"[TelegramTools] Baglanti hatasi: {_e}")
            raise

    def mesaj_gonder(self, chat_id: str, mesaj: str) -> str:
        """Belirtilen sohbete mesaj gonder.

        Args:
            chat_id: Hedef sohbet ID'si
            mesaj: Gonderilecek mesaj metni

        Returns:
            Islem sonucu mesaji
        """
        try:
            if not mesaj:
                return "[TelegramTools] Mesaj bos, gonderilmedi."
            yanit = self._api_istek("sendMessage", {
                "chat_id": chat_id,
                "text": mesaj,
                "parse_mode": "HTML",
            })
            mesaj_id = yanit.get("result", {}).get("message_id", 0)
            return f"[TelegramTools] Mesaj gonderildi (ID: {mesaj_id})"
        except RuntimeError as e:
            return f"[TelegramTools] Hata: {e}"
        except Exception as e:
            logger.exception("Beklenmeyen hata")
            return f"[TelegramTools] Beklenmeyen hata: {e}"

    def mesaj_oku(self, limit: int = 10) -> list:
        """Son mesajlari oku.

        Args:
            limit: Okunacak maksimum mesaj sayisi (varsayilan: 10)

        Returns:
            Mesaj listesi. Her mesaj: {"kimden": str, "metin": str, "tarih": int}
        """
        try:
            if limit < 1:
                limit = 1
            if limit > 100:
                limit = 100

            yanit = self._api_istek("getUpdates", {
                "offset": self._son_mesaj_id,
                "limit": limit,
                "timeout": 10,
            })
            sonuclar = yanit.get("result", [])
            mesajlar = []

            for guncelleme in sonuclar:
                update_id = guncelleme.get("update_id", 0)
                if update_id > self._son_mesaj_id:
                    self._son_mesaj_id = update_id + 1

                mesaj_verisi = guncelleme.get("message", {})
                if mesaj_verisi:
                    mesajlar.append({
                        "kimden": mesaj_verisi.get("from", {}).get("first_name", "Bilinmiyor"),
                        "metin": mesaj_verisi.get("text", ""),
                        "tarih": mesaj_verisi.get("date", 0),
                    })

            return mesajlar
        except RuntimeError as e:
            logger.warning("Mesaj okuma hatasi: %s", e)
            return []
        except Exception as e:
            logger.exception("Beklenmeyen okuma hatasi")
            return []

    def dosya_gonder(self, chat_id: str, dosya_yolu: str) -> str:
        """Sohbete dosya gonder.

        Args:
            chat_id: Hedef sohbet ID'si
            dosya_yolu: Gonderilecek dosyanin yolu

        Returns:
            Islem sonucu mesaji
        """
        try:
            if not os.path.exists(dosya_yolu):
                return f"[TelegramTools] Dosya bulunamadi: {dosya_yolu}"

            import requests
            dosya_adi = os.path.basename(dosya_yolu)

            with open(dosya_yolu, "rb") as f:
                r = requests.post(
                    f"{self._base_url}/sendDocument",
                    data={"chat_id": chat_id},
                    files={"document": (dosya_adi, f)},
                    timeout=self._timeout,
                )
                r.raise_for_status()
                yanit = r.json()
                if yanit.get("ok"):
                    doc_id = yanit.get("result", {}).get("document", {}).get("file_id", "")
                    return f"[TelegramTools] Dosya gonderildi (file_id: {doc_id})"
                return f"[TelegramTools] Dosya gonderilemedi: {yanit.get('description', '')}"
        except ImportError:
            return "[TelegramTools] requests kutuphanesi gerekli."
        except RuntimeError as e:
            return f"[TelegramTools] Hata: {e}"
        except Exception as e:
            logger.exception("Dosya gonderme hatasi")
            return f"[TelegramTools] Beklenmeyen hata: {e}"

    def ping(self) -> str:
        """Telegram API baglantisini test et.

        Returns:
            Baglanti durumu mesaji
        """
        try:
            import requests
            baslangic = time.time()
            r = requests.get(f"{self._base_url}/getMe", timeout=10)
            gecen_sure = round((time.time() - baslangic) * 1000, 1)
            r.raise_for_status()
            yanit = r.json()
            if yanit.get("ok"):
                bot_info = yanit.get("result", {})
                bot_ad = bot_info.get("first_name", "Bilinmiyor")
                kullanici_adi = bot_info.get("username", "")
                return (f"[TelegramTools] Baglanti basarili | Bot: {bot_ad} "
                        f"(@{kullanici_adi}) | Gecikme: {gecen_sure}ms")
            return f"[TelegramTools] Baglanti basarisiz: {yanit.get('description', '')}"
        except ImportError:
            return "[TelegramTools] requests kutuphanesi gerekli."
        except requests.exceptions.Timeout:
            return "[TelegramTools] Ping zamani asimi."
        except requests.exceptions.ConnectionError:
            return "[TelegramTools] Baglanti kurulamadi (internet yok?)."
        except Exception as e:
            return f"[TelegramTools] Ping hatasi: {e}"

    def sohbet_bilgisi(self, chat_id: str) -> dict:
        """Sohbet hakkinda bilgi al.

        Args:
            chat_id: Sohbet ID'si

        Returns:
            Sohbet bilgisi sozlugu
        """
        try:
            yanit = self._api_istek("getChat", {"chat_id": chat_id})
            sonuc = yanit.get("result", {})
            return {
                "id": sonuc.get("id", ""),
                "tip": sonuc.get("type", ""),
                "baslik": sonuc.get("title", ""),
                "kullanici_adi": sonuc.get("username", ""),
            }
        except RuntimeError as e:
            return {"hata": str(e)}
        except Exception as e:
            return {"hata": str(e)}

    def stream_mesaj_gonder(self, chat_id: str, mesaj: str, chunk_boyut: int = 4096) -> str:
        """Uzun mesajlari chunk'lara bolerek gonder.

        Args:
            chat_id: Hedef sohbet ID'si
            mesaj: Gonderilecek mesaj metni
            chunk_boyut: Her chunk'in maksimum karakter sayisi (varsayilan: 4096)

        Returns:
            Islem sonucu mesaji
        """
        try:
            if not mesaj:
                return "[TelegramTools] Mesaj bos, gonderilmedi."

            # Gateway import'u dene (basarili olursa gateway send_stream kullanilir)
            try:
                from gateway.platforms.telegram import send_stream
                stream_sonuc = send_stream(self._token, chat_id, mesaj)
                if isinstance(stream_sonuc, dict):
                    return f"Stream mesaj gonderildi ({stream_sonuc.get('chunk_sayisi', '?')} chunk)"
                return str(stream_sonuc)
            except ImportError as _e:
                logger.warning("[AraclarTelegram] Modul yuklenemedi (L263): %s", ImportError)
                pass

            # Kisa mesaj -> normal mesaj_gonder'e yonlendir
            if len(mesaj) <= chunk_boyut:
                return self.mesaj_gonder(chat_id, mesaj)

            # Uzun mesaj -> chunk'lara bol
            import requests
            chunk_sayisi = 0
            for i in range(0, len(mesaj), chunk_boyut):
                chunk = mesaj[i:i + chunk_boyut]
                data = {"chat_id": chat_id, "text": chunk}
                r = requests.post(f"{self._base_url}/sendMessage", data=data, timeout=self._timeout)
                r.raise_for_status()
                chunk_sayisi += 1

            return f"[TelegramTools] Mesaj chunk'landi ve gonderildi ({chunk_sayisi} chunk)"
        except RuntimeError as e:
            return f"[TelegramTools] Hata: {e}"
        except Exception as e:
            logger.exception("Stream mesaj gonderme hatasi")
            return f"[TelegramTools] Beklenmeyen hata: {e}"

    def reaction_ekle(self, chat_id: str, mesaj_id: int, emoji: str = "👍") -> str:
        """Mesaja reaction (emoji tepki) ekle.

        Args:
            chat_id: Sohbet ID'si
            mesaj_id: Mesaj ID'si
            emoji: Reaction emojisi (varsayilan: thumbsup)

        Returns:
            Islem sonucu mesaji
        """
        try:
            # Gateway import'u dene
            try:
                from gateway.platforms.telegram import set_reaction
                reac_sonuc = set_reaction(self._token, chat_id, mesaj_id, emoji)
                if isinstance(reac_sonuc, dict):
                    return f"Reaction eklendi: {emoji}"
                return str(reac_sonuc)
            except ImportError as _e:
                logger.warning("[AraclarTelegram] Modul yuklenemedi (L306): %s", ImportError)
                pass

            # Fallback: Telegram API setMessageReaction
            import requests
            data = {
                "chat_id": chat_id,
                "message_id": mesaj_id,
                "reaction": [{"type": "emoji", "emoji": emoji}],
            }
            r = requests.post(f"{self._base_url}/setMessageReaction", data=data, timeout=self._timeout)
            r.raise_for_status()
            return f"[TelegramTools] Reaction eklendi: {emoji}"
        except RuntimeError as e:
            return f"[TelegramTools] Hata: {e}"
        except Exception as e:
            logger.exception("Reaction ekleme hatasi")
            return f"[TelegramTools] Beklenmeyen hata: {e}"

    def mesaj_sil(self, chat_id: str, mesaj_id: int) -> str:
        """Mesaji sil.

        Args:
            chat_id: Sohbet ID'si
            mesaj_id: Silinecek mesajin ID'si

        Returns:
            Islem sonucu
        """
        try:
            self._api_istek("deleteMessage", {
                "chat_id": chat_id,
                "message_id": mesaj_id,
            })
            return f"[TelegramTools] Mesaj {mesaj_id} silindi."
        except RuntimeError as e:
            return f"[TelegramTools] Silme hatasi: {e}"
        except Exception as e:
            return f"[TelegramTools] Hata: {e}"


def run(**kwargs) -> str:
    """TelegramTools sinifini calistir.

    Args:
        **kwargs: Su parametreler desteklenir:
            - islem: "gonder", "oku", "ping", "dosya_gonder"
            - chat_id: Hedef sohbet ID'si
            - mesaj: Gonderilecek mesaj metni
            - limit: Okunacak mesaj sayisi
            - dosya_yolu: Gonderilecek dosya yolu

    Returns:
        Islem sonucu metni
    """
    try:
        bot = TelegramTools(
            token=kwargs.get("token"),
            chat_id=kwargs.get("chat_id"),
        )
        islem = kwargs.get("islem", "ping")

        if islem == "gonder":
            return bot.mesaj_gonder(
                chat_id=kwargs.get("chat_id", bot._chat_id),
                mesaj=kwargs.get("mesaj", ""),
            )
        elif islem == "oku":
            mesajlar = bot.mesaj_oku(limit=kwargs.get("limit", 10))
            return json.dumps(mesajlar, ensure_ascii=False, indent=2)
        elif islem == "dosya_gonder":
            return bot.dosya_gonder(
                chat_id=kwargs.get("chat_id", bot._chat_id),
                dosya_yolu=kwargs.get("dosya_yolu", ""),
            )
        elif islem == "bilgi":
            bilgi = bot.sohbet_bilgisi(kwargs.get("chat_id", ""))
            return json.dumps(bilgi, ensure_ascii=False, indent=2)
        elif islem == "stream":
            return bot.stream_mesaj_gonder(
                chat_id=kwargs.get("chat_id", bot._chat_id),
                mesaj=kwargs.get("mesaj", ""),
            )
        elif islem == "reaction":
            return bot.reaction_ekle(
                chat_id=kwargs.get("chat_id", bot._chat_id),
                mesaj_id=kwargs.get("mesaj_id", 0),
                emoji=kwargs.get("emoji", "👍"),
            )
        else:
            return bot.ping()
    except Exception as e:
        return f"[TelegramTools] Calistirma hatasi: {e}"


if __name__ == "__main__":
    bot = TelegramTools()
    print("=== Telegram Tools Test ===")
    print(bot.ping())
    print(bot.mesaj_gonder("test123", "Bu bir test mesajidir."))
    print(bot.mesaj_oku(limit=5))
    print(bot.dosya_gonder("test123", __file__))
    print("=== Test Tamam ===")
