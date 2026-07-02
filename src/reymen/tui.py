# -*- coding: utf-8 -*-
"""
tui.py — ReYMeN Terminal UI (prompt_toolkit tabanli).

Renkli, etkilesimli terminal arayuzu. Rich + prompt_toolkit ile:
  - Alt panelde komut giris satiri (prompt_toolkit)
  - Ust panelde konusma gecmisi (Rich Live)
  - Canli status bar (calisma suresi, mesaj sayisi, baglanti)
  - Klavye kisayollari
  - Otomatik tamamlama
  - Renkli cikti (syntax highlighting)
  - Log viewer (son N log)
  - Konfirmasyon dialog
  - Progress bar

Kullanim:
    from reymen.tui import ReYMeNTUI
    tui = ReYMeNTUI()
    tui.baslat()
"""
from __future__ import annotations

import logging
import shlex
import sys
import time
from typing import Any

logger = logging.getLogger(__name__)

# ── Opsiyonel bagimliliklar ──────────────────────────────────────────────

try:
    from prompt_toolkit import PromptSession, Application
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout import (
        Layout, HSplit, VSplit, Window, WindowAlign,
        FormattedTextControl, FloatContainer, Float,
    )
    from prompt_toolkit.styles import Style
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.completion import WordCompleter, FuzzyWordCompleter
    from prompt_toolkit.application import get_app
    PTK_AVAILABLE = True
except ImportError:
    PTK_AVAILABLE = False

try:
    from rich.console import Console as _RichConsole
    from rich.markdown import Markdown
    from rich.syntax import Syntax
    from rich.text import Text as _RichText
    from rich.table import Table as _RichTable
    from rich.panel import Panel as _RichPanel
    from rich.live import Live as _RichLive
    from rich.layout import Layout as _RichLayout
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


# ── Varsayilan Stil ──────────────────────────────────────────────────────

_STIL = Style.from_dict({
    "status":      "ansigreen bold",
    "error":       "ansired bold",
    "warning":     "ansiyellow",
    "info":        "ansiblue",
    "prompt":      "ansicyan bold",
    "title":       "white bold",
    "konusma":     "",
    "zaman":       "ansibrightblack",
})


# ── Renkli Cikti (Rich yoksa fallback) ───────────────────────────────────

def _stil_renk(metin: str, stil: str = "") -> str:
    """ANSI renk kodu ekle (prompt_toolkit stili)."""
    if not stil:
        return metin
    return f"class:{stil}:{metin}"


# ── Ana TUI Sinifi ───────────────────────────────────────────────────────

class ReYMeNTUI:
    """ReYMeN Terminal UI — prompt_toolkit tabanli etkilesimli arayuz.

    Ozellikler:
      - Alt panel: komut giris satiri (otomatik tamamlama + gecmis)
      - Ust panel: konusma gecmisi (kaydirilabilir)
      - Renkli cikti: syntax highlighting, markdown destegi
      - Klavye kisayollari: Ctrl+C cikis, Tab tamamlama
      - Motor entegrasyonu: tool'lari otomatik tamamlama olarak ekle
    """

    def __init__(self, motor: Any = None, baslik: str = "ReYMeN TUI"):
        self.motor = motor
        self.baslik = baslik
        self._mesaj_kuyrugu: list[str] = []
        self._calisiyor = False
        self._baslama = time.time()

        # prompt_toolkit bilesenleri
        self._session: Any = None
        self._kb: Any = None
        self._app: Any = None
        self._layout: Any = None
        self._konusma_kontrol: Any = None
        self._durum_kontrol: Any = None

        # Otomatik tamamlama kelimeleri
        self._komutlar = [
            "ac", "aciklama", "ara", "baslat", "bitir", "clear", "cikis",
            "exit", "gorsel", "gorev", "hafiza", "help", "history",
            "ilerleme", "iptal", "kaydet", "komut", "ls", "merhaba",
            "neredesin", "ne yapabilirsin", "oku", "prompt", "resim",
            "selam", "sil", "sistem", "status", "test", "yardim", "yaz",
            "?",
        ]

        # Motor tool adlarini tamamlama listesine ekle
        if motor:
            araclar = getattr(motor, '_araclar', {})
            for arac_adi in araclar:
                if arac_adi.lower() not in self._komutlar:
                    self._komutlar.append(arac_adi.lower())

    # ── Layout Olusturma ──────────────────────────────────────────────

    def _layout_olustur(self) -> Layout:
        """Ana layout: ust panel konusma + alt panel giris."""
        # Ust panel — konusma gecmisi
        self._konusma_kontrol = FormattedTextControl(
            text=self._mesaj_metni,
            focusable=False,
        )
        konusma_pencere = Window(
            content=self._konusma_kontrol,
            wrap_lines=True,
            always_hide_cursor=True,
            style="bg:#1a1a2e #e0e0e0",
        )

        # Alt panel — komut giris satiri
        self._giris_kontrol = FormattedTextControl(
            text="",
            focusable=True,
        )
        giris_pencere = Window(
            content=self._giris_kontrol,
            height=3,
            style="bg:#16213e #00ff88 bold",
            align=WindowAlign.LEFT,
        )

        # Ana layout
        self._layout = Layout(
            HSplit([
                konusma_pencere,
                giris_pencere,
            ])
        )
        return self._layout

    def _mesaj_metni(self) -> list[tuple[str, str]]:
        """Konusma penceresi icin formattli metin."""
        sonuc: list[tuple[str, str]] = [
            ("class:title", f"\n  {self.baslik}\n"),
            ("class:zaman", f"  {'='*40}\n"),
        ]
        for mesaj in self._mesaj_kuyrugu[-50:]:  # Son 50 mesaj
            sonuc.append(("class:konusma", f"  {mesaj}\n"))
        sonuc.append(("class:zaman", f"\n  {'-'*40}\n"))
        sonuc.append(("", "  > "))
        return sonuc

    # ── Klavye Kisayollari ───────────────────────────────────────────

    def _key_bindings(self) -> KeyBindings:
        kb = KeyBindings()

        @kb.add("c-c")
        def _cikis(event: Any) -> None:
            """Ctrl+C -> cikis."""
            self._calisiyor = False
            event.app.exit()

        @kb.add("c-d")
        def _cikis_eof(event: Any) -> None:
            """Ctrl+D -> cikis."""
            self._calisiyor = False
            event.app.exit()

        @kb.add("c-l")
        def _temizle(event: Any) -> None:
            """Ctrl+L -> ekrani temizle."""
            self._mesaj_kuyrugu.clear()

        @kb.add("enter")
        def _enter(event: Any) -> None:
            """Enter -> komutu isle."""
            giris = self._giris_kontrol.text.strip()
            self._giris_kontrol.text = ""
            if giris:
                self._mesaj_kuyrugu.append(f">>> {giris}")
                self._komut_islem(giris)
                self._konusma_kontrol.invalidate()

        return kb

    # ── Komut Isleme ─────────────────────────────────────────────────

    def _komut_islem(self, komut: str) -> None:
        """Kullanici komutunu isle."""
        komut = komut.strip()
        if not komut:
            return

        if komut in ("exit", "cikis", "q", "quit"):
            self.mesaj_ekle("[SISTEM] Gorusmek uzere!")
            self._calisiyor = False
            if self._app:
                self._app.exit()
            return

        if komut in ("clear", "temizle"):
            self._mesaj_kuyrugu.clear()
            return

        if komut in ("help", "yardim", "?"):
            self.mesaj_ekle("[YARDIM] Su komutlari kullanabilirsiniz:")
            self.mesaj_ekle("  selam / merhaba    - Selamlasma")
            self.mesaj_ekle("  status / durum     - Sistem durumu")
            self.mesaj_ekle("  clear / temizle    - Ekrani temizle")
            self.mesaj_ekle("  history            - Gecmis komutlar")
            self.mesaj_ekle("  exit / cikis       - Cikis")
            self.mesaj_ekle("  <tool_adi> <args>  - Motor tool'unu calistir")
            self.mesaj_ekle("  _                   - Yukaridaki mesaji tekrarla")
            return

        if komut in ("status", "durum"):
            self._status_goster()
            return

        if komut == "history":
            for i, m in enumerate(self._mesaj_kuyrugu[-20:], 1):
                self.mesaj_ekle(f"  {i}. {m}")
            return

        # Motor tool cagrisi dene
        if self.motor:
            try:
                sonuc = self._motor_cagir(komut)
                self.mesaj_ekle(sonuc)
                return
            except Exception as e:
                self.mesaj_ekle(f"[HATA] {e}")
                return

        # Motor yoksa basit sohbet
        self.mesaj_ekle(f"[ReyMeN] {komut}")

    def _motor_cagir(self, komut: str) -> str:
        """Motor tool'unu cagir. `TOOL_ADI arg1 arg2` formati.
        
        Motorun _araclar sozlugunde tool'u arar. Bulursa
        calistirir, bulamazsa conversation_loop/motor sohbete yonlendirir.
        """
        import shlex
        try:
            parcalar = shlex.split(komut)
        except ValueError:
            return "[HATA] Gecersiz komut formati"

        arac_adi = parcalar[0].upper() if parcalar else ""
        args = parcalar[1:] if len(parcalar) > 1 else []

        # 1) Motor tool registry'de ara
        araclar = getattr(self.motor, '_araclar', {})
        if arac_adi in araclar:
            try:
                tool_fn, aciklama = araclar[arac_adi]
                sonuc = tool_fn(args=args) if args else tool_fn()
                if sonuc is None:
                    return f"[TAMAM] {arac_adi} calisti (sonuc yok)"
                return str(sonuc)[:1000]
            except Exception as e:
                return f"[HATA] {arac_adi}: {e}"

        # 2) Motor.calistir dene
        if hasattr(self.motor, "calistir"):
            sonuc = self.motor.calistir(arac_adi, args)
            if sonuc:
                return str(sonuc)[:1000]

        # 3) Conversation loop'a gonder (dogrudan import)
        try:
            from reymen.cereyan.conversation_loop import ConversationLoop as _ConvLoop
            _cl = _ConvLoop(motor=self.motor)
            sonuc = _cl.coz(komut)
            if sonuc:
                yanit = sonuc.get("yanit", "") or str(sonuc)
                if yanit and not yanit.startswith("[") and len(yanit) > 3:
                    return yanit[:1000]
        except ImportError as _e:
            logger.warning("[Tui] Modul yuklenemedi (L308): %s", ImportError)
            pass
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )

        # 4) Basit sohbet
        return f"[ReyMeN] {komut}"

    def _status_goster(self) -> None:
        """Sistem durumu goster."""
        import datetime
        calisma = time.time() - self._baslama
        saat = int(calisma // 3600)
        dk = int((calisma % 3600) // 60)
        sn = int(calisma % 60)

        self.mesaj_ekle(f"[SISTEM] ReYMeN TUI")
        self.mesaj_ekle(f"  Calisma: {saat:02d}:{dk:02d}:{sn:02d}")
        self.mesaj_ekle(f"  Mesaj sayisi: {len(self._mesaj_kuyrugu)}")
        self.mesaj_ekle(f"  Rich: {'✅' if RICH_AVAILABLE else '❌'}")
        self.mesaj_ekle(f"  Prompt_toolkit: {'✅' if PTK_AVAILABLE else '❌'}")
        if self.motor:
            self.mesaj_ekle(f"  Motor: ✅ bagli")

    # ── Public API ────────────────────────────────────────────────────

    def mesaj_ekle(self, mesaj: str) -> None:
        """Konusma penceresine mesaj ekle."""
        self._mesaj_kuyrugu.append(mesaj)
        if self._konusma_kontrol:
            try:
                self._konusma_kontrol.invalidate()
            except Exception as _e:
                __import__("logging").getLogger(__name__).warning(
                    "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                )

    def baslat(self) -> None:
        """TUI'yi baslat ve event loop'a gir."""
        if not PTK_AVAILABLE:
            print("[TUI] prompt_toolkit kurulu degil. 'pip install prompt-toolkit'")
            print("[TUI] Fallback: basit REPL baslatiliyor...")
            self._repl_fallback()
            return

        self._calisiyor = True
        self._kb = self._key_bindings()
        self._layout = self._layout_olustur()

        # Tamamlama
        tamamlama = FuzzyWordCompleter(self._komutlar)

        # Session
        try:
            import os
            history_file = os.path.expanduser("~/.hermes/tui_history")
            self._session = PromptSession(
                history=FileHistory(history_file),
                auto_suggest=AutoSuggestFromHistory(),
                completer=tamamlama,
                key_bindings=self._kb,
                style=_STIL,
                enable_history_search=True,
            )

            self.mesaj_ekle(f"[SISTEM] ReYMeN TUI basladi. Yardim icin 'help' yazin.")
            self.mesaj_ekle(f"[SISTEM] Ctrl+C cikis, Ctrl+L temizle, Tab tamamlama.")

            # Ana loop
            while self._calisiyor:
                try:
                    giris = self._session.prompt(
                        " \n reymen> ",
                        style=_STIL,
                    )
                    if giris.strip():
                        self._mesaj_kuyrugu.append(f">>> {giris}")
                        self._komut_islem(giris)
                except (EOFError, KeyboardInterrupt):
                    continue

        except Exception as e:
            logger.error("TUI hatasi: %s", e)
            self._repl_fallback()

    def _repl_fallback(self) -> None:
        """prompt_toolkit yoksa basit REPL."""
        print("[TUI] Basit REPL (prompt_toolkit olmadan)")
        print("Yardim icin 'help' yazin, cikis icin 'exit'")
        self._calisiyor = True
        while self._calisiyor:
            try:
                giris = input("reymen> ").strip()
                if giris:
                    self._komut_islem(giris)
            except (EOFError, KeyboardInterrupt):
                print()
                break


# ── Kolaylik Fonksiyonlari (Geriye Uyumluluk) ────────────────────────────

def info(msg: str) -> None:
    if RICH_AVAILABLE:
        _RichConsole().print(f"[blue]ℹ[/blue] {msg}")
    else:
        print(f"[INFO] {msg}")


def success(msg: str) -> None:
    if RICH_AVAILABLE:
        _RichConsole().print(f"[green]✓[/green] {msg}")
    else:
        print(f"[OK] {msg}")


def warning(msg: str) -> None:
    if RICH_AVAILABLE:
        _RichConsole().print(f"[yellow]⚠[/yellow] {msg}")
    else:
        print(f"[WARN] {msg}")


def error(msg: str) -> None:
    if RICH_AVAILABLE:
        _RichConsole().print(f"[red]✗[/red] {msg}")
    else:
        print(f"[ERROR] {msg}", file=sys.stderr)


def panel(content: str, title: str | None = None, style: str = "cyan") -> None:
    if RICH_AVAILABLE:
        _RichConsole().print(_RichPanel(content, title=title, border_style=style))
    else:
        h = f"== {title} ==" if title else "========"
        print(h)
        print(content)
        print("=" * len(h))


def table(headers: list[str], rows: list[list[Any]], title: str | None = None) -> None:
    if RICH_AVAILABLE:
        t = _RichTable(title=title)
        for h in headers:
            t.add_column(str(h))
        for row in rows:
            t.add_row(*[str(c) for c in row])
        _RichConsole().print(t)
    else:
        if title:
            print(title)
        print(" | ".join(str(h) for h in headers))
        print("-" * 40)
        for row in rows:
            print(" | ".join(str(c) for c in row))


# ── Motor Kaydi ──────────────────────────────────────────────────────────

_TUI_MOTOR = None
_TUI_BEYIN = None


def motor_kaydet(motor, beyin=None) -> None:
    """Motor'a TUI baslatma araci kaydet ve motor/beyin referansini sakla."""
    global _TUI_MOTOR, _TUI_BEYIN
    _TUI_MOTOR = motor
    _TUI_BEYIN = beyin
    motor._plugin_arac_kaydet(
        "TUI_BASLAT", _tui_baslat,
        "Terminal UI'yi baslat. Parametre yok. "
        "prompt_toolkit + Rich ile etkilesimli arayuz."
    )
    motor._plugin_arac_kaydet(
        "TUI_MESAJ", _tui_mesaj,
        "TUI'ya mesaj gonder. Kullanim: TUI_MESAJ mesaj_metni"
    )
    motor._plugin_arac_kaydet(
        "TUI_DURUM", _tui_durum,
        "TUI durumunu goster: calisma suresi, mesaj sayisi, baglantilar"
    )
    logger.info("[TUI] Motor'a 3 arac kaydedildi (BASLAT, MESAJ, DURUM)")


_TUI_ORNEK: ReYMeNTUI | None = None


def _konusma_loop_olustur() -> Any:
    """Motor varsa ConversationLoop olustur, yoksa None."""
    if _TUI_MOTOR is None:
        return None
    try:
        from reymen.cereyan.conversation_loop import ConversationLoop
        if _TUI_BEYIN is not None:
            return ConversationLoop(motor=_TUI_MOTOR, beyin=_TUI_BEYIN)
        return ConversationLoop(motor=_TUI_MOTOR)
    except ImportError:
        return None


def _tui_baslat(**kw) -> str:
    """TUI'yi motor ile birlikte baslat."""
    global _TUI_ORNEK
    if _TUI_ORNEK is not None and _TUI_ORNEK._calisiyor:
        return "[TUI] Zaten calisiyor."
    tui = ReYMeNTUI(motor=_TUI_MOTOR, baslik="ReYMeN Terminal UI")
    _TUI_ORNEK = tui
    tui.baslat()
    _TUI_ORNEK = None
    return "[TUI] Terminal UI kapandi."


def _tui_mesaj(**kw) -> str:
    """TUI'ya mesaj gonder (TUI calisiyorsa)."""
    global _TUI_ORNEK
    if _TUI_ORNEK is None or not _TUI_ORNEK._calisiyor:
        mesaj = kw.get("_ham_metin", "") or kw.get("args", [""])[0] if isinstance(kw.get("args"), list) else str(kw.get("args", ""))
        print(f"[TUI] {mesaj}")
        return f"[TUI] Mesaj yazdirildi: {mesaj[:60]}"
    mesaj = kw.get("_ham_metin", "") or kw.get("args", [""])[0] if isinstance(kw.get("args"), list) else str(kw.get("args", ""))
    _TUI_ORNEK.mesaj_ekle(mesaj)
    return f"[TUI] Mesaj TUI'ya gonderildi: {mesaj[:60]}"


# ── with_spinner context manager ─────────────────────────────────────────

from contextlib import contextmanager


@contextmanager
def with_spinner(text: str = ""):
    """Context manager spinner (test uyumlulugu).

    Rich yoksa basit bir print yapar, sonra context'e devam eder.
    Kullanim:
        with with_spinner("Calisiyor..."):
            islem_yap()
    """
    if RICH_AVAILABLE:
        try:
            from rich.console import Console
            console = Console()
            with console.status(text, spinner="dots"):
                yield
        except Exception:
            print(f"[SPINNER] {text}...")
            yield
    else:
        print(f"[SPINNER] {text}...")
        yield


# ── progress_bar context manager (int-based) ─────────────────────────────


@contextmanager
def _progress_bar_cm(total: int, description: str = ""):
    """Context manager progress bar (int total ile).

    Kullanim:
        with progress_bar(10, "test") as advance:
            for _ in range(10):
                advance(1)
    """
    if RICH_AVAILABLE:
        try:
            from rich.console import Console
            from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn

            console = Console()
            with Progress(
                TextColumn(f"[bold cyan]{description}"),
                BarColumn(),
                TextColumn("{task.completed}/{task.total}"),
                TimeElapsedColumn(),
                console=console,
                transient=True,
            ) as p:
                task = p.add_task("", total=total)
                done = [0]

                def _advance(n: int = 1):
                    done[0] += n
                    p.update(task, completed=done[0])

                yield _advance
        except Exception:
            yield lambda n=1: None
    else:
        yield lambda n=1: None


def progress_bar(*args, **kwargs):
    """Progress bar — hem context manager (int total) hem iterable wrapper.

    * progress_bar(10, "test") -> context manager with advance(n)
    * progress_bar([1,2,3], "test") -> iterable wrapper (orijinal)
    """
    if args and isinstance(args[0], int):
        return _progress_bar_cm(*args, **kwargs)
    # Orijinal iterable wrapper (line 631+)
    return _progress_bar_iter(*args, **kwargs)


# ── Status Bar ──────────────────────────────────────────────────────────

class StatusBar:
    """Canli status bar (Rich Live ile alt satirda gostergeler).

    Kullanim:
        bar = StatusBar()
        bar.baslat()
        bar.guncelle(mesaj="Calisiyor...", durum="aktif")
        bar.durdur()
    """

    def __init__(self):
        self._live = None
        self._calisiyor = False
        self._baslama = time.time()
        self._son_mesaj = ""
        self._durum = "hazir"

    def baslat(self):
        if not RICH_AVAILABLE:
            return
        from rich.console import Console
        from rich.live import Live
        from rich.text import Text
        self._calisiyor = True
        console = Console()
        self._live = Live(self._metin_uret, console=console, refresh_per_second=4, transient=True)
        self._live.start()

    def guncelle(self, mesaj: str = "", durum: str = "aktif"):
        self._son_mesaj = mesaj
        self._durum = durum

    def _metin_uret(self) -> Any:
        if not RICH_AVAILABLE:
            return ""
        from rich.text import Text
        gecen = time.time() - self._baslama
        saat = int(gecen // 3600)
        dk = int((gecen % 3600) // 60)
        sn = int(gecen % 60)
        t = Text()
        t.append(f" ReYMeN TUI ", style="bold cyan")
        t.append(f"| {saat:02d}:{dk:02d}:{sn:02d} ", style="green")
        durum_stil = "green" if self._durum == "aktif" else "yellow" if self._durum == "bekliyor" else "red"
        t.append(f"| {self._durum.upper()} ", style=durum_stil)
        if self._son_mesaj:
            t.append(f"| {self._son_mesaj[:40]} ", style="white")
        return t

    def durdur(self):
        self._calisiyor = False
        if self._live:
            try:
                self._live.stop()
            except Exception as _e:
                __import__("logging").getLogger(__name__).warning(
                    "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                )


# ── Konfirmasyon Dialog ────────────────────────────────────────────────

def confirm(mesaj: str, varsayilan: bool = False, timeout: int = 0) -> bool:
    """Kullanicidan Evet/Hayir onayi iste.

    Args:
        mesaj: Gosterilecek soru.
        varsayilan: Zaman asiminda kullanilacak deger.
        timeout: Saniye cinsinden zaman asimi (0 = sonsuz).

    Returns:
        True (evet) veya False (hayir).
    """
    print()
    print(f"  \033[1;33m⚠ ONAY\033[0m")
    print(f"  {mesaj}")
    if timeout > 0:
        print(f"  [{timeout}sn icinde cevap verilmezse {'evet' if varsayilan else 'hayir'}]")
    print()

    try:
        import threading
        cevap = [None]

        def _oku():
            try:
                c = input("  Devam edilsin mi? [e/H] > ").strip().lower()
                cevap[0] = c in ("e", "evet", "y", "yes")
            except Exception:
                cevap[0] = varsayilan

        t = threading.Thread(target=_oku, daemon=True)
        t.start()
        t.join(timeout=timeout if timeout > 0 else None)

        if cevap[0] is None:
            print(f"  [Zaman asimi] {'Evet' if varsayilan else 'Hayir'} kabul edildi.")
            return varsayilan
        return bool(cevap[0])
    except Exception:
        return varsayilan


# ── Progress Bar (iterable wrapper, original API) ────────────────────────

def _progress_bar_iter(iterable, aciklama: str = "Isleniyor", renk: str = "cyan") -> Any:
    """Rich Progress bar ile iterasyon.

    Kullanim:
        for item in progress_bar(items, "Dosyalar taranıyor"):
            islem(item)

    Rich yoksa duz iterasyon doner.
    """
    if RICH_AVAILABLE:
        from rich.console import Console
        from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn
        console = Console()
        with Progress(
            TextColumn(f"[bold {renk}]{aciklama}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=console,
            transient=True,
        ) as p:
            task = p.add_task("", total=len(list(iterable)) if hasattr(iterable, "__len__") else None)
            for item in iterable:
                yield item
                p.advance(task)
    else:
        yield from iterable


# ── Log Viewer ──────────────────────────────────────────────────────────

class LogViewer:
    """Son N log satirini canli gosterir.

    Kullanim:
        viewer = LogViewer()
        viewer.ekle("INFO: Sistem basladi")
        viewer.goster(son=10)
    """

    def __init__(self, max_log: int = 100):
        self._loglar: list[str] = []
        self._max = max_log

    def ekle(self, satir: str) -> None:
        """Log ekle (max siniri asinca eskiyi sil)."""
        self._loglar.append(satir)
        if len(self._loglar) > self._max:
            self._loglar = self._loglar[-self._max:]

    def goster(self, son: int = 20, filtre: str | None = None) -> str:
        """Son N log satirini dondur (opsiyonel filtre ile)."""
        logs = self._loglar
        if filtre:
            logs = [l for l in logs if filtre.lower() in l.lower()]
        son_loglar = logs[-son:]
        if not son_loglar:
            return "[Log] Kayit yok."
        return "\n".join(f"  {l}" for l in son_loglar)

    def temizle(self) -> None:
        self._loglar.clear()

    def son(self, n: int = 5) -> list[str]:
        return self._loglar[-n:]


# ── Global LogViewer (istege bagli) ─────────────────────────────────────
_LOG_VIEWER = LogViewer()


def log_ekle(satir: str) -> None:
    """Global log viewer'a satir ekle."""
    _LOG_VIEWER.ekle(satir)


def log_goster(son: int = 20, filtre: str | None = None) -> str:
    """Global log viewer'dan son N satiri goster."""
    return _LOG_VIEWER.goster(son, filtre)
    mesaj = kw.get("_ham_metin", "") or kw.get("args", [""])[0] if isinstance(kw.get("args"), list) else str(kw.get("args", ""))
    _TUI_ORNEK.mesaj_ekle(f"[SISTEM] {mesaj}")
    return f"[TUI] Mesaj iletildi: {mesaj[:60]}"


def _tui_durum(**kw) -> str:
    """TUI durumunu goster."""
    global _TUI_ORNEK, _TUI_MOTOR
    satirlar = []
    if _TUI_ORNEK and _TUI_ORNEK._calisiyor:
        calisma = time.time() - _TUI_ORNEK._baslama
        satirlar.append(f"  TUI: AKTIF ({int(calisma)}s)")
        satirlar.append(f"  Mesaj: {len(_TUI_ORNEK._mesaj_kuyrugu)}")
    else:
        satirlar.append("  TUI: PASIF")
    if _TUI_MOTOR:
        satirlar.append(f"  Motor: {'bagli' if _TUI_MOTOR else 'bagli degil'}")
        tool_sayisi = len(getattr(_TUI_MOTOR, '_araclar', {}))
        satirlar.append(f"  Tool: {tool_sayisi}")
    return "\n".join(satirlar)


# ── CLI Giris ────────────────────────────────────────────────────────────

def main(motor: Any = None):
    """CLI'den TUI baslat.
    
    Args:
        motor: Motor instance (opsiyonel). Verilirse tool ve konusma destegi eklenir.
    """
    tui = ReYMeNTUI(motor=motor, baslik="ReYMeN TUI")
    tui.baslat()


if __name__ == "__main__":
    main()
