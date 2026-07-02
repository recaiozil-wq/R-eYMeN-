# -*- coding: utf-8 -*-
"""reymen.cli.tui — ReYMeN Terminal UI (TUI).

Rich tabanli terminal arayüzü.
- Panel, Table, Layout, Live Display
- Slash komutlar: /help, /model, /clear, /exit
- Tab ile otomatik tamamlama
- Durum çubuğu (model, provider, süre, token sayisi)
- Windows ile tam uyumlu (colorama + prompt_toolkit)
"""

from __future__ import annotations

import os
import sys
import time
import threading
from pathlib import Path
from typing import Optional, Callable

# ── Renk sabitleri (ANSI fallback) ────────────────────────────────────────
_R = "\033[0m"
_G = "\033[92m"
_C = "\033[96m"
_Y = "\033[93m"
_B = "\033[94m"
_M = "\033[95m"
_D = "\033[2m"
_RED = "\033[91m"
_W = "\033[97m"


def _g(t): return f"{_G}{t}{_R}"
def _c(t): return f"{_C}{t}{_R}"
def _y(t): return f"{_Y}{t}{_R}"
def _mavi(t): return f"{_B}{t}{_R}"
def _d(t): return f"{_D}{t}{_R}"
def _r(t): return f"{_RED}{t}{_R}"


# ── Durum verisi (synchronized) ───────────────────────────────────────────
class StatusData:
    """TUI durum çubuğu için thread-safe veri tutucu."""

    def __init__(self):
        self._lock = threading.Lock()
        self.model = "deepseek-v4-flash"
        self.provider = "deepseek"
        self.sure = "0s"
        self.token_giris = 0
        self.token_cikis = 0
        self._durum = "hazir"

    def guncelle(self, model: str = None, provider: str = None,
                 sure: str = None, token_giris: int = None,
                 token_cikis: int = None, durum: str = None):
        with self._lock:
            if model is not None:
                self.model = model
            if provider is not None:
                self.provider = provider
            if sure is not None:
                self.sure = sure
            if token_giris is not None:
                self.token_giris = token_giris
            if token_cikis is not None:
                self.token_cikis = token_cikis
            if durum is not None:
                self._durum = durum

    def kopyala(self) -> dict:
        with self._lock:
            return {
                "model": self.model,
                "provider": self.provider,
                "sure": self.sure,
                "token_giris": self.token_giris,
                "token_cikis": self.token_cikis,
                "durum": self._durum,
            }


# ── Rich TUI ana sinif ────────────────────────────────────────────────────
class ReYMeNTUI:
    """ReYMeN TUI ana sinifi.

    Rich Layout + Live Display ile terminal arayüzü.
    prompt_toolkit ile klavye girdisi ve otomatik tamamlama.

    Kullanim:
        tui = ReYMeNTUI(soru_callback=soru_fonksiyonu)
        tui.calistir()
    """

    def __init__(self, soru_callback: Callable = None,
                 model: str = "deepseek-v4-flash",
                 provider: str = "deepseek",
                 session_id: str = ""):
        self.soru_callback = soru_callback
        self.session_id = session_id or os.urandom(4).hex()
        self.status = StatusData()
        self.status.guncelle(model=model, provider=provider)

        self._calisiyor = threading.Event()
        self._calisiyor.set()
        self._mesaj_kuyrugu: list[tuple[str, str]] = []  # (tip, icerik)
        self._kuyruk_kilit = threading.Lock()
        self._son_soru = ""
        self._son_cevap = ""

        # Rich bilesenleri (gec yukleme)
        self._rich_console = None
        self._rich_layout = None
        self._live = None

        # prompt_toolki (gec yukleme)
        self._pt_session = None

    # ── Mesaj kuyrugu ────────────────────────────────────────────────────
    def mesaj_ekle(self, tip: str, icerik: str):
        """Thread-safe mesaj kuyruğuna ekle."""
        with self._kuyruk_kilit:
            self._mesaj_kuyrugu.append((tip, icerik))
            if len(self._mesaj_kuyrugu) > 200:
                self._mesaj_kuyrugu = self._mesaj_kuyrugu[-100:]

    def mesajlari_al(self) -> list[tuple[str, str]]:
        """Thread-safe mesaj kuyruğunu oku ve temizle."""
        with self._kuyruk_kilit:
            msj = list(self._mesaj_kuyrugu)
            self._mesaj_kuyrugu = []
            return msj

    # ── Rich layout olusturma ────────────────────────────────────────────
    def _layout_olustur(self):
        """Rich Layout bilesenlerini kur."""
        from rich.layout import Layout
        from rich.panel import Panel
        from rich.console import Console, Group
        from rich.table import Table
        from rich.text import Text
        from rich.align import Align

        # Ana layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=9),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=3),
        )

        # ── Header: Logo + Bilgi ─────────────────────────────────────────
        logo = (
            "[bold #FFD700]██████╗ ███████╗██╗   ██╗███╗   ███╗███████╗███╗   ██╗[/]\n"
            "[bold #FFD700]██╔══██╗██╔════╝╚██╗ ██╔╝████╗ ████║██╔════╝████╗  ██║[/]\n"
            "[#FFBF00]██████╔╝█████╗   ╚████╔╝ ██╔████╔██║█████╗  ██╔██╗ ██║[/]\n"
            "[#FFBF00]██╔══██╗██╔══╝    ╚██╔╝  ██║╚██╔╝██║██╔══╝  ██║╚██╗██║[/]\n"
            "[#CD7F32]██║  ██║███████╗   ██║   ██║ ╚═╝ ██║███████╗██║ ╚████║[/]\n"
            "[#CD7F32]╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝     ╚═╝╚══════╝╚═╝  ╚═══╝[/]"
        )
        durum = self.status.kopyala()
        info_tablo = Table.grid(padding=(0, 2))
        info_tablo.add_column(style="dim cyan", width=14)
        info_tablo.add_column(style="white")
        info_tablo.add_row("Model", f"[bold green]{durum['model']}[/]")
        info_tablo.add_row("Provider", f"[yellow]{durum['provider']}[/]")
        info_tablo.add_row("Oturum", f"[dim]{self.session_id}[/]")

        header_icerik = Group(
            Text.from_markup(logo),
            Panel(info_tablo, border_style="dim", title="[bold]ReYMeN TUI[/]"),
        )
        layout["header"].update(header_icerik)

        # ── Body: Sohbet alani ───────────────────────────────────────────
        body_panel = Panel(
            "[dim]ReYMeN Ajan'a hoş geldiniz! Mesajınızı yazın veya /yardim yazın.[/]",
            title="[bold]Sohbet[/]",
            border_style="blue",
        )
        layout["body"].update(body_panel)

        # ── Footer: Durum cubugu ─────────────────────────────────────────
        footer_tablo = Table.grid(padding=(0, 2))
        footer_tablo.add_column(style="dim", width=12)
        footer_tablo.add_column(style="green", width=24)
        footer_tablo.add_column(style="dim", width=10)
        footer_tablo.add_column(style="yellow", width=24)
        footer_tablo.add_column(style="dim", width=10)
        footer_tablo.add_column(style="cyan", width=16)

        footer_tablo.add_row(
            "Model:", durum["model"],
            "Provider:", durum["provider"],
            "Süre:", durum["sure"],
        )

        # Komut ipucu
        ipucu = Text.from_markup("[dim]/yardim  /model  /temizle  /cik[/]")

        footer_icerik = Group(
            Panel(footer_tablo, border_style="dim", title="[bold]Durum[/]"),
            Align.right(ipucu),
        )
        layout["footer"].update(footer_icerik)

        self._rich_layout = layout
        return layout

    def _body_guncelle(self, icerik: str):
        """Body panelini guncelle (en son mesajlarla)."""
        from rich.panel import Panel
        from rich.text import Text

        layout = getattr(self, "_rich_layout", None)
        if layout is None:
            return

        # Son 30 satiri goster
        satirlar = icerik.strip().split("\n")
        if len(satirlar) > 30:
            satirlar = satirlar[-30:]
        goster = "\n".join(satirlar)

        body_panel = Panel(
            Text.from_markup(goster) if goster else "[dim]Henüz mesaj yok.[/]",
            title="[bold]Sohbet[/]",
            border_style="blue",
        )
        layout["body"].update(body_panel)

    def _footer_guncelle(self):
        """Footer durum cubugunu guncelle."""
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
        from rich.align import Align
        from rich.console import Group

        durum = self.status.kopyala()
        layout = getattr(self, "_rich_layout", None)
        if layout is None:
            return

        footer_tablo = Table.grid(padding=(0, 2))
        footer_tablo.add_column(style="dim", width=12)
        footer_tablo.add_column(style="green", width=24)
        footer_tablo.add_column(style="dim", width=10)
        footer_tablo.add_column(style="yellow", width=24)
        footer_tablo.add_column(style="dim", width=10)
        footer_tablo.add_column(style="cyan", width=16)

        durum_ikon = "🟢" if durum["durum"] == "hazir" else "🟡"
        footer_tablo.add_row(
            f"{durum_ikon} Model:", durum["model"],
            "Provider:", durum["provider"],
            "Süre:", durum["sure"],
        )

        # Token bilgisi (varsa)
        if durum["token_giris"] > 0 or durum["token_cikis"] > 0:
            footer_tablo.add_row(
                "", "",
                "Token G:", str(durum["token_giris"]),
                "Token C:", str(durum["token_cikis"]),
            )

        ipucu = Text.from_markup("[dim]/yardim  /model  /temizle  /cik[/]")
        footer_icerik = Group(
            Panel(footer_tablo, border_style="dim", title="[bold]Durum[/]"),
            Align.right(ipucu),
        )
        layout["footer"].update(footer_icerik)

    # ── Sohbet gecmisi bicimle ───────────────────────────────────────────
    def _sohbet_metni(self) -> str:
        """Sohbet gecmisini bicimlenmis metin olarak dondur."""
        satirlar = []
        if self._son_soru:
            satirlar.append(f"[bold cyan]Siz >[/] {self._son_soru[:200]}")
        if self._son_cevap:
            satirlar.append(f"[bold green]ReYMeN >[/] {self._son_cevap[:2000]}")
        return "\n\n".join(satirlar) if satirlar else ""

    # ── Ana dongu ────────────────────────────────────────────────────────
    def calistir(self):
        """TUI'yi baslat ve ana girdi dongusunu calistir.

        Bu metot thread'de calisir; `Live` display arka planda guncellenir.
        """
        # Colorama'yi Windows'ta etkinlestir
        if os.name == "nt":
            try:
                import colorama
                colorama.init()
            except ImportError:
                pass

        from rich.console import Console
        from rich.live import Live

        console = Console()
        self._rich_console = console

        # Layout olustur
        layout = self._layout_olustur()

        # Windows'ta ANSI destegi
        if os.name == "nt" and not os.environ.get("TERM"):
            os.environ["TERM"] = "xterm-256color"

        # Live display ile baslat
        with Live(layout, console=console, refresh_per_second=8,
                  screen=True, auto_refresh=False) as live:
            self._live = live
            self._live.refresh()

            # prompt_toolkit ile girdi dongusu
            try:
                self._girdi_dongusu(live)
            except KeyboardInterrupt:
                pass
            except EOFError:
                pass
            finally:
                self._live = None

        # Colorama temizligi
        if os.name == "nt":
            try:
                import colorama
                colorama.deinit()
            except ImportError:
                pass

    def _girdi_dongusu(self, live):
        """prompt_toolkit ile girdi al ve isle."""
        has_prompt_toolkit = False
        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.completion import WordCompleter
            from prompt_toolkit.history import InMemoryHistory
            from prompt_toolkit.key_binding import KeyBindings
            from prompt_toolkit.keys import Keys
            has_prompt_toolkit = True
        except ImportError:
            has_prompt_toolkit = False

        if has_prompt_toolkit:
            self._girdi_dongusu_ptk(live)
        else:
            self._girdi_dongusu_basic(live)

    def _girdi_dongusu_ptk(self, live):
        """prompt_toolkit ile gelismis girdi dongusu (tab tamamlama dahil)."""
        from prompt_toolkit import PromptSession
        from prompt_toolkit.completion import WordCompleter
        from prompt_toolkit.history import InMemoryHistory
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.keys import Keys
        from prompt_toolkit.formatted_text import HTML
        from prompt_toolkit.styles import Style

        # Otomatik tamamlama kelimeleri
        komutlar = [
            "/yardim", "/help", "/?",
            "/model",
            "/temizle", "/cls", "/clear",
            "/cik", "/çık", "/exit", "/quit",
            "/provider",
            "/durum", "/status",
            "/token",
            "/versiyon", "/version",
        ]

        completer = WordCompleter(komutlar, ignore_case=True)
        history = InMemoryHistory()

        # Klavye baglantilari
        kb = KeyBindings()

        @kb.add("c-c")
        def _cikis_cc(event):
            """Ctrl+C ile cikis."""
            event.app.exit(result="")

        @kb.add("c-d")
        def _cikis_cd(event):
            """Ctrl+D ile cikis."""
            event.app.exit(result="")

        # Stil
        stil = Style.from_dict({
            "prompt": "bold cyan",
        })

        # Prompt HTML
        def _prompt_html():
            durum = self.status.kopyala()
            return HTML(f"<prompt>ReYMeN ></prompt> ")

        session = PromptSession(
            history=history,
            completer=completer,
            key_bindings=kb,
            style=stil,
            complete_while_typing=True,
            Vi_mode=False,
            enable_open_in_editor=False,
        )

        while self._calisiyor.is_set():
            try:
                # Girilen yeni mesajlari isle (Live guncellemesi)
                yeni_mesajlar = self.mesajlari_al()
                for tip, icerik in yeni_mesajlar:
                    if tip == "soru":
                        self._son_soru = icerik
                    elif tip == "cevap":
                        self._son_cevap = icerik
                    self._body_guncelle(self._sohbet_metni())
                    self._footer_guncelle()
                    live.refresh()

                # Girdi al
                girdi = session.prompt(
                    _prompt_html(),
                    bottom_toolbar=HTML(
                        f"<b>Model:</b> {self.status.kopyala()['model']} | "
                        f"<b>Süre:</b> {self.status.kopyala()['sure']}"
                    ),
                )

                girdi = girdi.strip()
                if not girdi:
                    continue

                # Slash komutlar
                if self._slash_komut_isle(girdi, live):
                    continue

                # Soruyu callback'e gonder
                if self.soru_callback:
                    self.mesaj_ekle("soru", girdi)
                    self._son_soru = girdi
                    self.status.guncelle(durum="calisiyor")
                    self._footer_guncelle()
                    live.refresh()

                    t0 = time.time()
                    cevap = self.soru_callback(girdi)
                    dt = time.time() - t0

                    self._son_cevap = cevap
                    self.mesaj_ekle("cevap", cevap)
                    sure_str = f"{dt:.1f}s"
                    self.status.guncelle(sure=sure_str, durum="hazir")
                    self._body_guncelle(self._sohbet_metni())
                    self._footer_guncelle()
                    live.refresh()

            except (EOFError, KeyboardInterrupt):
                break

    def _girdi_dongusu_basic(self, live):
        """input() ile basit girdi dongusu (prompt_toolkit yoksa)."""
        print("\n" * 2)
        print(f"  {_d('[TUI] prompt_toolkit yuklu degil. input() kullaniliyor.')}")
        print(f"  {_d('pip install prompt_toolkit ile tab tamamlama ekleyebilirsiniz.')}")
        print()

        while self._calisiyor.is_set():
            try:
                # Bekleyen mesajlari isle
                yeni_mesajlar = self.mesajlari_al()
                for tip, icerik in yeni_mesajlar:
                    if tip == "soru":
                        self._son_soru = icerik
                    elif tip == "cevap":
                        self._son_cevap = icerik
                    self._body_guncelle(self._sohbet_metni())
                    self._footer_guncelle()
                    live.refresh()

                # Live ekrani gecici kapat, soru al
                live.stop()

                # Basit ipucu ile girdi
                sys.stdout.write(f"\r  {_g('ReYMeN')} > ")
                sys.stdout.flush()
                try:
                    girdi = sys.stdin.readline()
                except (EOFError, KeyboardInterrupt):
                    print()
                    break

                if not girdi:
                    break
                girdi = girdi.strip()

                # Live devam
                live.start()
                live.refresh()

                if not girdi:
                    continue

                if self._slash_komut_isle(girdi, live):
                    continue

                if self.soru_callback:
                    self.mesaj_ekle("soru", girdi)
                    self._son_soru = girdi
                    self.status.guncelle(durum="calisiyor")
                    self._footer_guncelle()
                    live.refresh()

                    t0 = time.time()
                    cevap = self.soru_callback(girdi)
                    dt = time.time() - t0

                    self._son_cevap = cevap
                    self.mesaj_ekle("cevap", cevap)
                    sure_str = f"{dt:.1f}s"
                    self.status.guncelle(sure=sure_str, durum="hazir")
                    self._body_guncelle(self._sohbet_metni())
                    self._footer_guncelle()
                    live.refresh()

            except (EOFError, KeyboardInterrupt):
                break

    # ── Slash komutlar ───────────────────────────────────────────────────
    def _slash_komut_isle(self, girdi: str, live) -> bool:
        """Slash komutlari isle. Komut islendiyse True don."""
        from rich.panel import Panel
        from rich.text import Text
        from rich.table import Table

        g = girdi.lower().strip()

        # /cik, /exit, /quit
        if g in ("/cik", "/çık", "/exit", "/quit", "/q"):
            self._calisiyor.clear()
            return True

        # /yardim, /help
        if g in ("/yardim", "/help", "/?"):
            yardim_text = (
                "[bold]ReYMeN TUI Komutlari[/]\n\n"
                "[cyan]/yardim[/]  veya [cyan]/help[/]   Bu menüyü göster\n"
                "[cyan]/model[/]                     Model değiştir\n"
                "[cyan]/provider[/]                  Provider değiştir\n"
                "[cyan]/temizle[/]  veya [cyan]/clear[/]   Ekranı temizle\n"
                "[cyan]/durum[/]    veya [cyan]/status[/]  Durum bilgisi\n"
                "[cyan]/token[/]                     Token sayaci sifirla\n"
                "[cyan]/cik[/]     veya [cyan]/exit[/]    Çıkış\n\n"
                "[dim]Herhangi bir metin yaz → ReYMeN cevaplar.[/]"
            )
            panel = Panel(
                Text.from_markup(yardim_text),
                title="[bold #FFD700]Yardim[/]",
                border_style="yellow",
            )
            self._body_guncelle(panel)  # type: ignore
            live.refresh()
            return True

        # /temizle, /clear
        if g in ("/temizle", "/cls", "/clear"):
            self._son_soru = ""
            self._son_cevap = ""
            self._body_guncelle("[dim]Ekran temizlendi.[/]")
            live.refresh()
            return True

        # /model
        if g.startswith("/model"):
            from rich.table import Table

            model_bilgi = (
                "[bold yellow]Mevcut Model:[/] "
                f"[green]{self.status.kopyala()['model']}[/]\n\n"
                "[dim]Model değiştirmek için .env dosyasindaki\n"
                "REYMEN_MODEL değişkenini güncelleyip\n"
                "yeniden başlatın.[/]"
            )
            panel = Panel(
                Text.from_markup(model_bilgi),
                title="[bold]Model Bilgisi[/]",
                border_style="green",
            )
            self._body_guncelle(panel)  # type: ignore
            live.refresh()
            return True

        # /provider
        if g.startswith("/provider"):
            prov_bilgi = (
                "[bold yellow]Mevcut Provider:[/] "
                f"[green]{self.status.kopyala()['provider']}[/]\n\n"
                "[dim]Provider değiştirmek için .env dosyasindaki\n"
                "REYMEN_PROVIDER değişkenini güncelleyip\n"
                "yeniden başlatın.[/]"
            )
            panel = Panel(
                Text.from_markup(prov_bilgi),
                title="[bold]Provider Bilgisi[/]",
                border_style="green",
            )
            self._body_guncelle(panel)  # type: ignore
            live.refresh()
            return True

        # /durum, /status
        if g in ("/durum", "/status"):
            durum = self.status.kopyala()
            tablo = Table.grid(padding=(0, 2))
            tablo.add_column(style="cyan", width=14)
            tablo.add_column(style="white")
            tablo.add_row("Model", durum["model"])
            tablo.add_row("Provider", durum["provider"])
            tablo.add_row("Süre", durum["sure"])
            tablo.add_row("Token Giriş", str(durum["token_giris"]))
            tablo.add_row("Token Çıkış", str(durum["token_cikis"]))
            tablo.add_row("Durum", durum["durum"])
            panel = Panel(
                tablo,
                title="[bold]Durum[/]",
                border_style="cyan",
            )
            self._body_guncelle(panel)  # type: ignore
            live.refresh()
            return True

        # /token
        if g in ("/token",):
            self.status.guncelle(token_giris=0, token_cikis=0)
            panel = Panel(
                Text.from_markup("[green]Token sayaci sifirlandi.[/]"),
                title="[bold]Token[/]",
                border_style="green",
            )
            self._body_guncelle(panel)  # type: ignore
            live.refresh()
            return True

        # /versiyon
        if g in ("/versiyon", "/version"):
            panel = Panel(
                Text.from_markup(
                    "[yellow]ReYMeN Agent[/] v0.1.0\n"
                    f"[dim]Model: {self.status.kopyala()['model']}[/]\n"
                    f"[dim]Python: {sys.version.split()[0]}[/]"
                ),
                title="[bold]Versiyon[/]",
                border_style="magenta",
            )
            self._body_guncelle(panel)  # type: ignore
            live.refresh()
            return True

        return False

    def dur(self):
        """TUI'yi durdur."""
        self._calisiyor.clear()


# ── Kolay kullanim fonksiyonu ─────────────────────────────────────────────
def tui_baslat(soru_callback: Callable = None,
               model: str = "deepseek-v4-flash",
               provider: str = "deepseek",
               session_id: str = "") -> int:
    """TUI'yi baslat.

    Args:
        soru_callback: (soru: str) -> cevap: str seklinde fonksiyon
        model: Baslangic model adi
        provider: Baslangic provider adi
        session_id: Oturum ID'si (bos birakilirsa otomatik)

    Returns:
        0 basarili, 1 hata
    """
    try:
        tui = ReYMeNTUI(
            soru_callback=soru_callback,
            model=model,
            provider=provider,
            session_id=session_id,
        )
        tui.calistir()
        return 0
    except ImportError as e:
        print(f"  {_r('[HATA]')} TUI icin gerekli paket yuklu degil: {e}")
        print(f"  {_y('pip install rich')}")
        return 1
    except Exception as e:
        print(f"  {_r('[HATA]')} TUI hatasi: {e}")
        return 1


# ── Dogrudan calistirma (test) ────────────────────────────────────────────
if __name__ == "__main__":
    def _test_soru(soru: str) -> str:
        return f"Test cevap: '{soru}' icin isleniyor..."

    sys.exit(tui_baslat(soru_callback=_test_soru))
