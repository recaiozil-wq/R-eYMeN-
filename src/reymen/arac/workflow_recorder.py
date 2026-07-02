# -*- coding: utf-8 -*-
"""workflow_recorder.py — İş akışı kaydetme ve tekrarlama.

Browser işlemlerini kaydeder, JSON dosyasına yazar,
sonra aynı adımları sırayla tekrarlar.

Kullanım:
    rec = WorkflowRecorder()
    rec.basla("test")
    rec.kaydet("ac", url="https://example.com")
    rec.kaydet("tikla", secici="#btn")
    rec.bitir()
    rec.tekrarla("test", browser_tool)
"""

import json
import time
import os
from pathlib import Path

WORKFLOW_DIR = Path(__file__).parent / "workflows"
WORKFLOW_DIR.mkdir(exist_ok=True)


class WorkflowRecorder:
    """Browser iş akışlarını kaydet ve tekrarla."""

    def __init__(self):
        self._adimlar: list = []
        self._kayit_yapiliyor: bool = False
        self._workflow_adi: str = ""

    def basla(self, workflow_adi: str) -> str:
        """Kaydı başlat.

        Args:
            workflow_adi: Workflow adı (dosya adı olarak kullanılır)

        Returns:
            str: Durum mesajı
        """
        ad = workflow_adi.strip() or f"workflow_{int(time.time())}"
        self._adimlar = []
        self._kayit_yapiliyor = True
        self._workflow_adi = ad
        return f"[Workflow] 🔴 Kayit basladi: {ad}"

    def kaydet(self, adim_turu: str, **kwargs) -> None:
        """Her browser işlemini kaydet (aktif kayıt varsa).

        Args:
            adim_turu: İşlem türü (ac, tikla, fill, scroll, bekle, ...)
            **kwargs: İşlem parametreleri
        """
        if not self._kayit_yapiliyor:
            return
        self._adimlar.append({
            "tur": adim_turu,
            "zaman": time.time(),
            **kwargs
        })

    def bitir(self) -> str:
        """Kaydı bitir ve JSON dosyasına yaz.

        Returns:
            str: Durum mesajı
        """
        if not self._kayit_yapiliyor:
            return "[Workflow] Aktif kayit yok."
        if not self._adimlar:
            self._kayit_yapiliyor = False
            return "[Workflow] Kaydedilecek adim yok."

        dosya = WORKFLOW_DIR / f"{self._workflow_adi}.json"
        data = {
            "adi": self._workflow_adi,
            "tarih": time.strftime("%Y-%m-%d %H:%M:%S"),
            "adim_sayisi": len(self._adimlar),
            "adimlar": self._adimlar,
        }
        dosya.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self._kayit_yapiliyor = False
        return f"[Workflow] ✅ Kaydedildi: {dosya.name} ({len(self._adimlar)} adim)"

    def iptal(self) -> str:
        """Aktif kaydı kaydetmeden iptal et."""
        if not self._kayit_yapiliyor:
            return "[Workflow] Aktif kayit yok."
        self._adimlar = []
        self._kayit_yapiliyor = False
        self._workflow_adi = ""
        return "[Workflow] Kayit iptal edildi."

    def tekrarla(self, workflow_adi: str, browser_tool) -> str:
        """Kayıtlı workflow'u tekrarla.

        Args:
            workflow_adi: Workflow adı (dosya adı, .json'suz)
            browser_tool: BrowserTool instance'ı

        Returns:
            str: İşlem raporu
        """
        dosya = WORKFLOW_DIR / f"{workflow_adi}.json"
        if not dosya.exists():
            return f"[Workflow] ❌ Bulunamadi: {workflow_adi}"

        data = json.loads(dosya.read_text(encoding="utf-8"))
        satirlar = [
            f"[Workflow] ▶️ Tekrar basliyor: {data['adi']} ({data['adim_sayisi']} adim)"
        ]

        for i, adim in enumerate(data["adimlar"]):
            tur = adim["tur"]
            try:
                if tur == "ac":
                    browser_tool.ac(adim.get("url", ""))
                    satirlar.append(f"  [{i+1}] ✅ ac: {adim.get('url','')[:60]}")
                elif tur == "tikla":
                    browser_tool.tikla(adim["secici"])
                    satirlar.append(f"  [{i+1}] ✅ tikla: {adim.get('secici','')[:50]}")
                elif tur == "fill":
                    browser_tool.fill(adim["secici"], adim["deger"])
                    satirlar.append(f"  [{i+1}] ✅ fill: {adim.get('secici','')[:30]}")
                elif tur == "type":
                    browser_tool.type_text(adim["secici"], adim["deger"])
                    satirlar.append(f"  [{i+1}] ✅ type: {adim.get('secici','')[:30]}")
                elif tur == "scroll":
                    browser_tool.scroll(dy=adim.get("dy", 300))
                    satirlar.append(f"  [{i+1}] ✅ scroll: {adim.get('dy',300)}px")
                elif tur == "bekle":
                    time.sleep(adim.get("sure", 1))
                    satirlar.append(f"  [{i+1}] ✅ bekle: {adim.get('sure',1)}s")
                elif tur == "sec":
                    browser_tool.select_option(adim["secici"], adim["deger"])
                    satirlar.append(f"  [{i+1}] ✅ sec: {adim.get('secici','')[:30]}")
                elif tur == "hover":
                    browser_tool.hover(adim["secici"])
                    satirlar.append(f"  [{i+1}] ✅ hover: {adim.get('secici','')[:30]}")
                elif tur == "screenshot":
                    browser_tool.screenshot(adim.get("url", ""), adim.get("cikti", "screenshot.png"))
                    satirlar.append(f"  [{i+1}] ✅ screenshot")
                elif tur == "back":
                    browser_tool.back()
                    satirlar.append(f"  [{i+1}] ✅ back")
                elif tur == "forward":
                    browser_tool.forward()
                    satirlar.append(f"  [{i+1}] ✅ forward")
                elif tur == "geribildirim":
                    # Kullanıcıya mesaj göster (sadece log)
                    satirlar.append(f"  [{i+1}] 💬 {adim.get('mesaj','')}")
                else:
                    satirlar.append(f"  [{i+1}] ⚠️ Bilinmeyen adim: {tur}")
            except Exception as e:
                satirlar.append(f"  [{i+1}] ❌ {tur}: {e}")
                break

        satirlar.append(f"[Workflow] {'✅ Tamam' if '❌' not in satirlar[-1] else '❌ Yari'}")
        return "\n".join(satirlar)

    def listele(self) -> str:
        """Kayıtlı tüm workflow'ları listele.

        Returns:
            str: Workflow listesi
        """
        dosyalar = sorted(WORKFLOW_DIR.glob("*.json"))
        if not dosyalar:
            return "[Workflow] Kayitli workflow yok."
        satirlar = [f"[Workflow] 📋 {len(dosyalar)} kayit:"]
        for d in dosyalar:
            try:
                data = json.loads(d.read_text(encoding="utf-8"))
                satirlar.append(
                    f"  • {data['adi']} ({data['adim_sayisi']} adim, {data['tarih']})"
                )
            except (json.JSONDecodeError, KeyError):
                satirlar.append(f"  • {d.stem} (bozuk dosya)")
        return "\n".join(satirlar)

    def sil(self, workflow_adi: str) -> str:
        """Bir workflow'u sil.

        Args:
            workflow_adi: Silinecek workflow adı

        Returns:
            str: Durum mesajı
        """
        dosya = WORKFLOW_DIR / f"{workflow_adi}.json"
        if not dosya.exists():
            return f"[Workflow] Bulunamadi: {workflow_adi}"
        dosya.unlink()
        return f"[Workflow] Silindi: {workflow_adi}"
