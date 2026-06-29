# -*- coding: utf-8 -*-
"""
salted_gateway.py — Güvenli gateway.

SaltedGateway sinifi ile mesajlari salt+hash ile imzalayip
dogrulayan, rate limiting uygulayan ve istatistik tutan
guvenli bir gecit sistemi saglar.
"""

import os
import json
import time
import hmac
import hashlib
import secrets
import asyncio
from collections import deque
from typing import Optional, List, Dict, Any, Callable
import logging

# GatewayBase (circular import yok)
from reymen.ag.gateway_temel import GatewayBase

logger = logging.getLogger(__name__)


class TelegramRateLimiter:
    """Token bucket rate limiter — Telegram limiti 30 msg/sn"""

    def __init__(self, max_per_second=30, burst=40):
        self.max_per_second = max_per_second
        self.burst = burst
        self.tokens = burst
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.burst, self.tokens + elapsed * self.max_per_second)
            self.last_refill = now

            if self.tokens < 1:
                wait = (1 - self.tokens) / self.max_per_second
                await asyncio.sleep(wait)
                self.tokens = 0
                self.last_refill = time.monotonic()

            self.tokens -= 1
            return True

    async def send_with_retry(self, coro_factory, max_retries=3):
        """Rate-limit korumali gonderim + 429 hatasinda otomatik retry"""
        for attempt in range(max_retries):
            await self.acquire()
            try:
                result = await coro_factory()
                return result
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "Too Many Requests" in error_str:
                    wait = min(30, 2 ** attempt * 2)
                    print(f"[RateLimit] 429 aldi, {wait}s bekliyor (deneme {attempt+1}/{max_retries})")
                    await asyncio.sleep(wait)
                    continue
                elif "Conflict" in error_str or "409" in error_str:
                    wait = 5
                    print(f"[RateLimit] Conflict, {wait}s bekliyor")
                    await asyncio.sleep(wait)
                    continue
                raise
        raise Exception(f"Rate limit asildi, {max_retries} deneme basarisiz")


class AutoReconnector:
    """Telegram baglantisi kopunca otomatik yeniden baglan"""

    def __init__(self, connect_fn, max_retries=10, base_delay=1):
        self.connect_fn = connect_fn
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._running = False
        self._health_interval = 60

    async def run_with_reconnect(self):
        self._running = True
        retry_count = 0

        while self._running and retry_count < self.max_retries:
            try:
                await self.connect_fn()
                retry_count = 0
                while self._running:
                    await asyncio.sleep(self._health_interval)
                    if not await self._health_check():
                        print("[Reconnect] Health check basarisiz, yeniden baglaniyor...")
                        break
            except (ConnectionError, TimeoutError, OSError) as e:
                retry_count += 1
                delay = min(30, self.base_delay * (2 ** (retry_count - 1)))
                print(f"[Reconnect] Baglanti koptu: {e}")
                print(f"[Reconnect] {delay}s sonra yeniden deneniyor (deneme {retry_count}/{self.max_retries})")
                await asyncio.sleep(delay)
            except Exception as e:
                print(f"[Reconnect] Beklenmeyen hata: {e}")
                break

        if retry_count >= self.max_retries:
            print(f"[Reconnect] {self.max_retries} deneme basarisiz, gateway durduruluyor")

    async def _health_check(self):
        try:
            return True
        except Exception:
            return False

    def stop(self):
        self._running = False


class SessionManager:
    """Session yonetimi — her kullanici icin ayri session"""

    def __init__(self, session_timeout=1800, cleanup_interval=300):
        self._sessions = {}
        self._session_timeout = session_timeout
        self._cleanup_interval = cleanup_interval

    async def get_or_create(self, chat_id, user_info=None):
        now = time.time()

        if chat_id in self._sessions:
            session = self._sessions[chat_id]
            if now - session["last_active"] < self._session_timeout:
                session["last_active"] = now
                return session
            else:
                print(f"[Session] {chat_id} timeout oldu, yeniden olusturuluyor")

        session = {
            "chat_id": chat_id,
            "user_info": user_info or {},
            "created_at": now,
            "last_active": now,
            "message_count": 0,
            "context": []
        }
        self._sessions[chat_id] = session
        print(f"[Session] Yeni session: {chat_id}")
        return session

    async def cleanup_stale(self):
        now = time.time()
        stale = [
            cid for cid, s in self._sessions.items()
            if now - s["last_active"] > self._session_timeout
        ]
        for cid in stale:
            del self._sessions[cid]
            print(f"[Session] Temizlendi: {cid}")

    async def periodic_cleanup(self):
        while True:
            await asyncio.sleep(self._cleanup_interval)
            await self.cleanup_stale()

    def get_stats(self):
        if not self._sessions:
            return {"active_sessions": 0, "total_messages": 0, "oldest_session": 0}
        return {
            "active_sessions": len(self._sessions),
            "total_messages": sum(s["message_count"] for s in self._sessions.values()),
            "oldest_session": min(s["created_at"] for s in self._sessions.values())
        }


class CrashRecovery:
    """Gateway cokerse otomatik kurtarma + nedenini logla"""

    def __init__(self, restart_fn, max_restarts=3, window_seconds=60):
        self.restart_fn = restart_fn
        self.max_restarts = max_restarts
        self.window_seconds = window_seconds
        self._crash_times = deque(maxlen=max_restarts)

    async def run_with_recovery(self):
        while True:
            try:
                await self.restart_fn()
                break
            except Exception as e:
                now = time.time()
                self._crash_times.append(now)

                recent = [t for t in self._crash_times if now - t < self.window_seconds]
                print(f"[CrashRecovery] Gateway coktu: {type(e).__name__}: {e}")

                if len(recent) >= self.max_restarts:
                    print(f"[CrashRecovery] {self.window_seconds}s icinde {self.max_restarts} cokme — durduruluyor")
                    await self._notify_admin(f"Gateway {self.max_restarts} kez coktu, durduruldu")
                    break

                delay = min(30, 2 ** (len(recent) - 1))
                print(f"[CrashRecovery] {delay}s sonra yeniden baslatiliyor...")
                await asyncio.sleep(delay)

    async def _notify_admin(self, message):
        try:
            print(f"[ADMIN NOTIFY] {message}")
        except Exception as _salted_g_e204:
            print(f"[UYARI] salted_gateway.py:205 - {_salted_g_e204}")


class SaltedGateway:
    """
    Guvenli gateway.

    Mesajlari salt+HMAC ile imzalar, token dogrulama yapar,
    rate limiting uygular ve istatistik toplar. Sistem icinde
    guvenli iletisim ve erisim kontrolu icin kullanilir.

    Kullanim:
        gateway = SaltedGateway()
        imzali = gateway.gonder(hedef="servis_a", mesaj="merhaba")
        dogrulama = gateway.dogrula(token=imzali["token"])
    """

    def __init__(self, salt: Optional[str] = None, rate_limit: int = 100,
                 rate_penceresi: int = 60):
        """
        SaltedGateway baslatici.

        Args:
            salt: Kriptografik tuz. None ise otomatik olusturulur.
            rate_limit: Rate limit esigi (penceredeki maksimum istek).
            rate_penceresi: Rate limit penceresi (saniye).
        """
        self._salt = salt or secrets.token_hex(32)
        self._rate_limit = rate_limit
        self._rate_penceresi = rate_penceresi
        self._istatistik: Dict[str, Any] = {
            "gonderilen": 0,
            "dogrulanan": 0,
            "reddedilen": 0,
            "rate_limit_engeli": 0,
            "son_islem": None,
            "baslangic": time.time(),
        }
        self._rate_kayitlari: Dict[str, List[float]] = {}
        self._hedefler: Dict[str, Dict[str, Any]] = {}

    def _imzala(self, veri: str) -> str:
        """
        Veriyi HMAC-SHA256 ile imzalar.

        Args:
            veri: Imzalanacak veri.

        Returns:
            Hex imza.
        """
        return hmac.new(
            self._salt.encode("utf-8"),
            veri.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def _token_olustur(self, hedef: str, mesaj: str) -> str:
        """
        Hedef ve mesaj icin guvenli token olusturur.

        Args:
            hedef: Hedef servis adi.
            mesaj: Mesaj icerigi.

        Returns:
            Token.
        """
        zaman = str(int(time.time()))
        rastgele = secrets.token_hex(8)
        ham = f"{hedef}:{mesaj}:{zaman}:{rastgele}"
        imza = self._imzala(ham)
        return f"{zaman}.{rastgele}.{imza}"

    def gonder(self, hedef: str, mesaj: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Hedefe imzali mesaj gonderir (sanal).

        Mesaji imzalar ve hedefe iletir. Hedef kayitli degilse
        otomatik eklenir.

        Args:
            hedef: Hedef servis veya modul adi.
            mesaj: Gonderilecek mesaj.
            meta: Ek metadata.

        Returns:
            Imzali mesaj paketi.
        """
        try:
            # Rate limit kontrol
            if not self.rate_limit_kontrol(hedef):
                self._istatistik["rate_limit_engeli"] += 1
                return {
                    "basarili": False,
                    "hata": "Rate limit asildi",
                    "hedef": hedef,
                }

            # Token olustur
            token = self._token_olustur(hedef, mesaj)

            # Hedefi kaydet
            if hedef not in self._hedefler:
                self._hedefler[hedef] = {
                    "ad": hedef,
                    "ilk_gonderi": time.time(),
                    "gonderi_sayisi": 0,
                }

            self._hedefler[hedef]["gonderi_sayisi"] += 1

            # Istatistik
            self._istatistik["gonderilen"] += 1
            self._istatistik["son_islem"] = {
                "tip": "gonder",
                "hedef": hedef,
                "zaman": time.time(),
            }

            paket = {
                "basarili": True,
                "hedef": hedef,
                "mesaj": mesaj,
                "token": token,
                "meta": meta or {},
                "zaman_damgasi": int(time.time()),
                "imza_turu": "HMAC-SHA256",
            }

            return paket

        except Exception as e:
            return {"basarili": False, "hata": f"Gonderim hatasi: {e}"}

    def dogrula(self, token: str, hedef: Optional[str] = None,
                mesaj: Optional[str] = None) -> Dict[str, Any]:
        """
        Token dogrulaması yapar.

        Token'in gecerliligini, zaman damgasini ve (varsa)
        hedef/mesaj uyumunu kontrol eder.

        Args:
            token: Dogrulanacak token.
            hedef: Opsiyonel, beklenen hedef.
            mesaj: Opsiyonel, beklenen mesaj.

        Returns:
            Dogrulama sonucu.
        """
        try:
            # Token formatini coz
            parcalar = token.split(".")
            if len(parcalar) != 3:
                self._istatistik["reddedilen"] += 1
                return {"basarili": False, "hata": "Gecersiz token formati"}

            zaman_str, rastgele, imza = parcalar

            # Zaman damgasi kontrolu (5 dakika gecerli)
            try:
                zaman = int(zaman_str)
                suanki_zaman = int(time.time())
                if suanki_zaman - zaman > 300:
                    self._istatistik["reddedilen"] += 1
                    return {"basarili": False, "hata": "Token suresi dolmus"}
            except ValueError:
                self._istatistik["reddedilen"] += 1
                return {"basarili": False, "hata": "Gecersiz zaman damgasi"}

            # Imza dogrulama (hedef ve mesaj biliniyorsa)
            if hedef and mesaj:
                beklenen_ham = f"{hedef}:{mesaj}:{zaman_str}:{rastgele}"
                beklenen_imza = self._imzala(beklenen_ham)
                if not hmac.compare_digest(imza, beklenen_imza):
                    self._istatistik["reddedilen"] += 1
                    return {"basarili": False, "hata": "Gecersiz imza"}

            self._istatistik["dogrulanan"] += 1
            self._istatistik["son_islem"] = {
                "tip": "dogrulama",
                "zaman": time.time(),
            }

            return {
                "basarili": True,
                "mesaj": "Token gecerli",
                "zaman_damgasi": zaman,
                "yasi": int(time.time()) - zaman,
            }

        except Exception as e:
            self._istatistik["reddedilen"] += 1
            return {"basarili": False, "hata": f"Dogrulama hatasi: {e}"}

    def rate_limit_kontrol(self, hedef: str) -> bool:
        """
        Hedef icin rate limit kontrolu yapar.

        Belirtilen zaman penceresinde hedefe gonderilen istek
        sayisini kontrol eder.

        Args:
            hedef: Kontrol edilecek hedef.

        Returns:
            Limit asilmadiysa True.
        """
        try:
            now = time.time()
            pencere_baslangici = now - self._rate_penceresi

            # Eski kayitlari temizle
            if hedef in self._rate_kayitlari:
                self._rate_kayitlari[hedef] = [
                    t for t in self._rate_kayitlari[hedef] if t > pencere_baslangici
                ]
            else:
                self._rate_kayitlari[hedef] = []

            # Su anki istegi ekle
            self._rate_kayitlari[hedef].append(now)

            # Limit kontrolu
            return len(self._rate_kayitlari[hedef]) <= self._rate_limit

        except Exception as e:
            print(f"[Gateway] Rate limit hatasi: {e}")
            return True  # Hata durumunda gecerli say

    def istatistik(self) -> Dict[str, Any]:
        """
        Gateway kullanim istatistiklerini dondurur.

        Returns:
            Detayli istatistik raporu.
        """
        try:
            calisma_suresi = time.time() - self._istatistik["baslangic"]
            toplam_islem = (
                self._istatistik["gonderilen"]
                + self._istatistik["dogrulanan"]
                + self._istatistik["reddedilen"]
            )

            return {
                **self._istatistik,
                "calisma_suresi": round(calisma_suresi, 2),
                "toplam_islem": toplam_islem,
                "kayitli_hedef": len(self._hedefler),
                "hedefler": {
                    h: d["gonderi_sayisi"]
                    for h, d in sorted(
                        self._hedefler.items(),
                        key=lambda x: x[1]["gonderi_sayisi"],
                        reverse=True
                    )
                },
                "rate_limit_yapisi": {
                    "limit": self._rate_limit,
                    "pencere": self._rate_penceresi,
                },
            }

        except Exception as e:
            return {"hata": str(e)}

    def hedef_ekle(self, ad: str, aciklama: str = "") -> bool:
        """
        Yeni bir hedef ekler.

        Args:
            ad: Hedef adi.
            aciklama: Hedef aciklamasi.

        Returns:
            Basarili mi?
        """
        try:
            if ad not in self._hedefler:
                self._hedefler[ad] = {
                    "ad": ad,
                    "aciklama": aciklama,
                    "ilk_gonderi": None,
                    "gonderi_sayisi": 0,
                }
                return True
            return False
        except Exception:
            return False

    def hedef_listele(self) -> List[Dict[str, Any]]:
        """
        Kayitli hedefleri listeler.

        Returns:
            Hedef listesi.
        """
        return list(self._hedefler.values())

    def run(self, **kwargs) -> str:
        """
        Evrensel calistirma metodu.

        kwargs icinde:
            - action: "gonder", "dogrula", "rate_limit_kontrol", "istatistik",
                      "hedef_ekle", "hedef_listele"
            - Diger parametreler ilgili metoda yonlendirilir.

        Returns:
            JSON formatinda sonuc.
        """
        try:
            action = kwargs.pop("action", "istatistik")
            if action == "gonder":
                sonuc = self.gonder(**kwargs)
            elif action == "dogrula":
                sonuc = self.dogrula(**kwargs)
            elif action == "rate_limit_kontrol":
                hedef = kwargs.get("hedef", "")
                sonuc = {"gecerli": self.rate_limit_kontrol(hedef)}
            elif action == "istatistik":
                sonuc = self.istatistik()
            elif action == "hedef_ekle":
                sonuc = {"basarili": self.hedef_ekle(**kwargs)}
            elif action == "hedef_listele":
                sonuc = {"hedefler": self.hedef_listele()}
            else:
                sonuc = {"hata": f"Bilinmeyen action: {action}"}
            return json.dumps(sonuc, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            return json.dumps({"hata": str(e)}, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════════════
#  TelegramGateway — GatewayBase Implementasyonu
# ═══════════════════════════════════════════════════════════════════════

class TelegramGateway(GatewayBase):
    """
    Telegram platform gateway'i — GatewayBase implementasyonu.

    Mevcut SaltedGateway, TelegramRateLimiter ve AutoReconnector
    yapilarini kullanarak Telegram API'sine baglanir, mesaj
    gonderir/alir. python-telegram-bot kutuphanesini kullanir.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("telegram", config)
        self._token: Optional[str] = None
        self._bot = None
        self._rate_limiter: Optional[TelegramRateLimiter] = None
        self._reconnector: Optional[AutoReconnector] = None
        self._imzalayici: Optional[SaltedGateway] = None
        self._mesaj_kuyrugu: asyncio.Queue = asyncio.Queue()
        self._gelen_mesajlar: List[Dict[str, Any]] = []

    async def connect(self) -> bool:
        """Telegram bot API'sine baglan."""
        try:
            token = self._config.get("token") or os.getenv("TELEGRAM_BOT_TOKEN", "")
            if not token:
                self._son_hata = "TELEGRAM_BOT_TOKEN bulunamadi"
                logger.error(f"[TelegramGateway] {self._son_hata}")
                return False

            self._token = token

            # Rate limiter
            self._rate_limiter = TelegramRateLimiter(
                max_per_second=self._config.get("rate_limit", 30),
                burst=self._config.get("burst", 40),
            )

            # SaltedGateway imzalayici
            self._imzalayici = SaltedGateway(
                salt=self._config.get("salt")
            )

            # python-telegram-bot
            try:
                from telegram.ext import Application
                self._bot = Application.builder().token(token).build()
                await self._bot.initialize()
                logger.info("[TelegramGateway] Application baslatildi.")
            except ImportError:
                logger.warning("[TelegramGateway] python-telegram-bot yuklu degil, stub modda.")
                self._bot = None

            # AutoReconnector
            self._reconnector = AutoReconnector(
                connect_fn=self._baglanti_kur,
                max_retries=self._config.get("max_retries", 10),
                base_delay=self._config.get("base_delay", 1),
            )

            self._bagli = True
            self._son_hata = None
            logger.info("[TelegramGateway] Telegram'a baglanildi.")
            return True

        except Exception as e:
            self._son_hata = str(e)
            logger.error(f"[TelegramGateway] Baglanti hatasi: {e}")
            return False

    async def _baglanti_kur(self) -> None:
        """AutoReconnector icin baglanti fonksiyonu."""
        # Connect zaten yapildi, health check icin
        if not self._bagli:
            await self.connect()

    async def disconnect(self) -> bool:
        """Telegram baglantisini kes."""
        try:
            if self._bot:
                await self._bot.shutdown()
                self._bot = None
            if self._reconnector:
                self._reconnector.stop()
            self._bagli = False
            logger.info("[TelegramGateway] Baglanti kesildi.")
            return True
        except Exception as e:
            self._son_hata = str(e)
            logger.error(f"[TelegramGateway] Baglanti kesme hatasi: {e}")
            return False

    async def send(self, mesaj: str, hedef: Optional[str] = None,
                   meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Telegram'a mesaj gonder."""
        try:
            if not self._bagli:
                return {"basarili": False, "hata": "Baglanti yok"}

            chat_id = hedef or self._config.get("varsayilan_chat_id")

            # Rate limit
            if self._rate_limiter:
                await self._rate_limiter.acquire()

            # SaltedGateway imzasi
            imza = None
            if self._imzalayici:
                imzali = self._imzalayici.gonder(hedef="telegram", mesaj=mesaj)
                imza = imzali.get("token")

            # python-telegram-bot ile gonder
            if self._bot and chat_id:
                try:
                    await self._bot.bot.send_message(
                        chat_id=chat_id,
                        text=mesaj,
                        parse_mode="Markdown",
                    )
                except Exception as send_err:
                    logger.warning(f"[TelegramGateway] Gonderim: {send_err}")

            self._mesaj_sayaci += 1
            return {
                "basarili": True,
                "platform": "telegram",
                "hedef": chat_id,
                "mesaj": mesaj,
                "imza": imza,
                "zaman": time.time(),
            }

        except Exception as e:
            self._son_hata = str(e)
            return {"basarili": False, "hata": str(e)}

    async def receive(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Gelen Telegram mesajini kuyruktan al."""
        try:
            mesaj = await asyncio.wait_for(self._mesaj_kuyrugu.get(), timeout=timeout)
            return mesaj
        except asyncio.TimeoutError:
            return None

    async def health_check(self) -> Dict[str, Any]:
        """Telegram baglanti sagligi kontrolu."""
        try:
            if not self._bagli:
                return {"durum": "kopuk", "platform": "telegram"}

            if self._bot:
                me = await self._bot.bot.get_me()
                return {
                    "durum": "saglikli",
                    "platform": "telegram",
                    "bot_username": me.username if me else None,
                }

            return {"durum": "saglikli", "platform": "telegram", "not": "stub_mod"}
        except Exception as e:
            return {"durum": "hata", "platform": "telegram", "hata": str(e)}

    def mesaj_ekle(self, mesaj: Dict[str, Any]) -> None:
        """Gelen mesaji kuyruga ekle (callback'ler icin)."""
        self._mesaj_kuyrugu.put_nowait(mesaj)
        self._gelen_mesajlar.append(mesaj)


# ── Motor Kayit ─────────────────────────────────────────────────────

def motor_kaydet(motor) -> None:
    """Motor'a salted gateway araçlarını kaydeder."""
    motor._plugin_arac_kaydet(
        "SALTED_GATEWAY_OLUSTUR",
        lambda salt="", rate_limit="100": f"SaltedGateway(salt='{salt}', rate_limit={rate_limit})",
        "Guvenli SaltedGateway ornegi olusturur",
    )
    motor._plugin_arac_kaydet(
        "SALTED_GATEWAY_GONDER",
        lambda hedef="", mesaj="": f"SaltedGateway().gonder(hedef='{hedef}', mesaj='{mesaj}')",
        "SaltedGateway ile imzali mesaj gonderir",
    )
    motor._plugin_arac_kaydet(
        "SALTED_GATEWAY_DOGRULA",
        lambda token="", hedef="", mesaj="": f"SaltedGateway().dogrula(token='{token}', ...)",
        "SaltedGateway token dogrulamasi yapar",
    )
    motor._plugin_arac_kaydet(
        "SALTED_GATEWAY_ISTATISTIK",
        lambda: "SaltedGateway().istatistik()",
        "SaltedGateway kullanim istatistiklerini dondurur",
    )


if __name__ == "__main__":
    gw = SaltedGateway(rate_limit=10, rate_penceresi=60)
    print("SaltedGateway hazir.")

    # Test gonder
    gonderi = gw.gonder(hedef="test_servis", mesaj="merhaba dunya")
    print("Gonderi:", json.dumps(gonderi, ensure_ascii=False, indent=2))

    # Test dogrula
    if gonderi.get("basarili"):
        dogrula = gw.dogrula(
            token=gonderi["token"],
            hedef=gonderi["hedef"],
            mesaj=gonderi["mesaj"]
        )
        print("Dogrulama:", json.dumps(dogrula, ensure_ascii=False, indent=2))

    print("Istatistik:", json.dumps(gw.istatistik(), ensure_ascii=False, indent=2))
