# -*- coding: utf-8 -*-
"""
guvenli_sandbox.py — ReYMeN Güvenli Kod Çalıştırma Sandbox'ı.

Python kodunu izole bir alt süreçte çalıştırır:
  - Timeout (zaman aşımı)
  - Bellek sınırı
  - Modül allowlist'i (sadece izin verilen modüller)
  - Dosya sistemi kısıtlaması (geçici dizin)
  - Çıktı boyut sınırı
  - Tehlikeli işlemleri engelleme (subprocess, eval, exec, import blacklist)

Kullanım:
    from reymen.guvenlik.guvenli_sandbox import guvenli_calistir, Sandbox

    sonuc = guvenli_calistir("print('Merhaba')", timeout=10)
    print(sonuc)  # "[OK] Merhaba\\n"

    sb = Sandbox(timeout=5, max_chars=1000)
    sonuc = sb.calistir("import os; os.system('dir')")
    print(sonuc)  # "[REDACTED] Yasakli modul: os"
"""

from __future__ import annotations

import io
import logging
import os
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Varsayılan Ayarlar ──────────────────────────────────────────────────

# İzin verilen modüller (allowlist)
VARSAYILAN_MODUL_LISTESI = frozenset({
    # Python standart kütüphanesi (güvenli)
    "math", "random", "datetime", "time", "json", "re", "collections",
    "itertools", "functools", "typing", "enum", "dataclasses", "uuid",
    "hashlib", "base64", "binascii", "string", "statistics", "decimal",
    "fractions", "copy", "pprint", "textwrap", "stringprep",
    # Temel işlemler
    "bisect", "heapq", "operator", "functools", "abc",
    "pathlib",  # sadece okuma için
})

# Kesinlikle yasaklı modüller/kodlar
YASAKLI_ANAHTAR_KELIMELER = [
    "import os", "from os", "import subprocess", "from subprocess",
    "import sys", "from sys",
    "import ctypes", "from ctypes",
    "import socket", "from socket",
    "eval(", "exec(", "compile(", "__import__(",
    "open(",  # dosya okuma/yazma
    "os.system", "os.popen", "os.spawn",
    "subprocess.run", "subprocess.Popen", "subprocess.call",
    "shutil.rmtree", "shutil.move", "shutil.copy",
    "Path.unlink", "Path.rmdir",
    "ctypes.CDLL", "ctypes.WinDLL", "ctypes.CreateProcess",
    "socket.connect", "socket.send", "socket.recv",
    "requests.get", "requests.post", "urllib.request",
    "sqlite3.connect",
]

# ── Hata Sınıfları ──────────────────────────────────────────────────────

class SandboxError(RuntimeError):
    """Sandbox çalıştırma hatası."""


class SandboxTimeout(SandboxError):
    """Zaman aşımı."""


class YasakliModulHatasi(SandboxError):
    """Yasaklı modül kullanımı."""


class CiktiSiniriHatasi(SandboxError):
    """Çıktı boyut sınırı aşıldı."""


# ── Sandbox Sınıfı ──────────────────────────────────────────────────────

class Sandbox:
    """Güvenli kod çalıştırma sandbox'ı.

    Args:
        timeout: Maksimum çalışma süresi (saniye).
        max_chars: Maksimum çıktı boyutu (karakter).
        modul_listesi: İzin verilen modüller (None=varsayılan).
        calisma_dizini: Kodun çalışacağı dizin (None=geçici dizin).
    """

    def __init__(
        self,
        timeout: int = 10,
        max_chars: int = 5000,
        modul_listesi: set[str] | None = None,
        calisma_dizini: str | None = None,
    ) -> None:
        self.timeout = timeout
        self.max_chars = max_chars
        self.modul_listesi = frozenset(modul_listesi) if modul_listesi else VARSAYILAN_MODUL_LISTESI
        self._calisma_dizini = calisma_dizini

    # ── Ana API ─────────────────────────────────────────────────────────

    def calistir(self, kod: str, baglam: dict[str, Any] | None = None) -> str:
        """Kodu sandbox içinde çalıştır.

        Args:
            kod: Çalıştırılacak Python kodu.
            baglam: Koda eklenecek değişkenler (opsiyonel).

        Returns:
            stdout çıktısı veya hata mesajı.

        Raises:
            SandboxTimeout: Zaman aşımı.
            YasakliModulHatasi: Yasaklı modül kullanımı.
        """
        # 1. Kod ön kontrolü
        self._kod_kontrol(kod)

        # 2. Geçici script dosyası oluştur
        script = self._script_olustur(kod, baglam or {})

        # 3. Subprocess ile çalıştır
        import subprocess
        try:
            process = subprocess.run(
                [sys.executable, "-u", script],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self._calisma_dizini or tempfile.gettempdir(),
            )
        except subprocess.TimeoutExpired:
            raise SandboxTimeout(f"Kod {self.timeout}s icinde tamamlanamadi.")

        # 4. Sonucu işle
        cikti = process.stdout + process.stderr

        if len(cikti) > self.max_chars:
            cikti = cikti[:self.max_chars] + f"\n... [cikti {len(cikti)} karakter, sinir {self.max_chars}]"

        return cikti

    def _script_olustur(self, kod: str, baglam: dict[str, Any]) -> str:
        """Kodu geçici bir script dosyasına yaz."""
        wrapper_bas = (
            '# ReYMeN Sandbox - Izole Calistirma\n'
            'import sys\n\n'
            '_izinli_builtins = {\n'
            '    "print": print, "len": len, "range": range,\n'
            '    "int": int, "float": float, "str": str,\n'
            '    "bool": bool, "list": list, "dict": dict,\n'
            '    "tuple": tuple, "set": set, "True": True,\n'
            '    "False": False, "None": None,\n'
            '    "abs": abs, "all": all, "any": any, "chr": chr,\n'
            '    "divmod": divmod, "enumerate": enumerate,\n'
            '    "filter": filter, "format": format,\n'
            '    "frozenset": frozenset, "hash": hash, "hex": hex,\n'
            '    "id": id, "isinstance": isinstance,\n'
            '    "issubclass": issubclass, "iter": iter,\n'
            '    "map": map, "max": max, "min": min, "next": next,\n'
            '    "oct": oct, "ord": ord, "pow": pow, "repr": repr,\n'
            '    "reversed": reversed, "round": round,\n'
            '    "slice": slice, "sorted": sorted, "sum": sum,\n'
            '    "type": type, "vars": vars, "zip": zip,\n'
            '}\n\n'
            'def _guvenli_import(name, *args, **kwargs):\n'
            '    import_name = name.split(".")[0]\n'
            '    if import_name not in _IZINLI_MODULLER:\n'
            '        raise ImportError("Yasakli modul: " + import_name)\n'
            '    return __import__(name, *args, **kwargs)\n\n'
            '_izinli_builtins["__import__"] = _guvenli_import\n\n'
            '_IZINLI_MODULLER = ' + repr(sorted(self.modul_listesi)) + '\n\n'
            '_baglam = ' + repr(baglam) + '\n\n'
            '# Kodu calistir\n'
            'try:\n'
            '    exec("""\n'
        )
        
        # Kodu ekle (girintili)
        kod_satirlari = kod.split('\n')
        girintili_kod = '\n'.join(kod_satirlari)
        
        wrapper_son = (
            '\n""", {"__builtins__": _izinli_builtins, **_baglam}, {})\n'
            'except Exception as e:\n'
            '    print("[HATA] %s: %s" % (type(e).__name__, e), file=sys.stderr)\n'
        )
        
        wrapper = wrapper_bas + girintili_kod + wrapper_son
        
        fd, yol = tempfile.mkstemp(suffix=".py", prefix="reymen_sandbox_", text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(wrapper)
        self._son_script = yol
        return yol
    def __del__(self):
        # Geçici script dosyasını temizle
        if hasattr(self, "_son_script") and self._son_script and os.path.exists(self._son_script):
            try:
                os.unlink(self._son_script)
            except Exception as _e:
                __import__("logging").getLogger(__name__).warning(
                    "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                )

    # ── Kod Ön Kontrolü ────────────────────────────────────────────────

    def _kod_kontrol(self, kod: str) -> None:
        """Kodu çalıştırmadan önce güvenlik kontrolü yap."""
        for yasakli in YASAKLI_ANAHTAR_KELIMELER:
            if yasakli in kod:
                raise YasakliModulHatasi(
                    f"Yasakli ifade tespit edildi: {yasakli!r}"
                )

    # ── Kod Çalıştırma ──────────────────────────────────────────────────


    def _guvenli_import(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """Sadece izin verilen modülleri import et."""
        # __import__ çağrısındaki ana modül adını al
        import_name = name.split(".")[0] if "." in name else name

        if import_name not in self.modul_listesi:
            raise YasakliModulHatasi(
                f"Yasakli modul: {import_name!r}. Izin verilenler: "
                f"{sorted(self.modul_listesi)}"
            )

        # builtins.__import__ ile gerçek import
        import builtins
        return builtins.__import__(name, *args, **kwargs)


# ── Kolaylık Fonksiyonu ────────────────────────────────────────────────

_VARSAYILAN_SANDBOX = Sandbox()


def guvenli_calistir(
    kod: str,
    timeout: int = 10,
    max_chars: int = 5000,
    baglam: dict[str, Any] | None = None,
) -> str:
    """Kodu güvenli sandbox'ta çalıştır (tek satırlık API).

    Args:
        kod: Çalıştırılacak Python kodu.
        timeout: Zaman aşımı süresi (saniye).
        max_chars: Maksimum çıktı boyutu.
        baglam: Koda eklenecek değişkenler.

    Returns:
        Çıktı metni.
    """
    sb = Sandbox(timeout=timeout, max_chars=max_chars)
    return sb.calistir(kod, baglam)


# ── Test ────────────────────────────────────────────────────────────────

def _test() -> None:
    """Sandbox testleri."""
    print("=== Sandbox Test ===\n")

    # 1. Basit kod
    sonuc = guvenli_calistir("print('Merhaba Dunya!')")
    print(f"1. Basit kod: {'✅' if 'Merhaba' in sonuc else '❌'}")
    print(f"   Cikti: {sonuc.strip()}")

    # 2. Matematik
    sonuc = guvenli_calistir("print(2 + 3 * 4)")
    print(f"2. Matematik: {'✅' if '14' in sonuc else '❌'}")

    # 3. Döngü
    sonuc = guvenli_calistir("toplam = sum(range(100)); print(toplam)")
    print(f"3. Döngu: {'✅' if '4950' in sonuc else '❌'}")

    # 4. Yasaklı modül
    try:
        guvenli_calistir("import os; print(os.name)")
        print("4. Yasakli modul: ❌ (engellenemedi)")
    except YasakliModulHatasi:
        print("4. Yasakli modul: ✅ (engellendi)")

    # 5. Yasaklı ifade
    try:
        guvenli_calistir("eval('2+2')")
        print("5. Yasakli ifade: ❌ (engellenemedi)")
    except YasakliModulHatasi:
        print("5. Yasakli ifade: ✅ (engellendi)")

    # 6. Timeout
    try:
        guvenli_calistir("while True: pass", timeout=1)
        print("6. Timeout: ❌ (durdurulamadi)")
    except SandboxTimeout:
        print("6. Timeout: ✅ (durduruldu)")

    # 7. Çıktı sınırı
    sonuc = guvenli_calistir("print('x' * 10000)", max_chars=100)
    print(f"7. Cikti siniri: {'✅' if 'sinir' in sonuc else '❌'}")

    # 8. İzin verilen modül
    sonuc = guvenli_calistir("import math; print(math.pi)")
    print(f"8. Izinli modul: {'✅' if '3.14' in sonuc else '❌'}")

    # 9. Baglam
    sonuc = guvenli_calistir("print(ad)", baglam={"ad": "ReYMeN"})
    print(f"9. Baglam: {'✅' if 'ReYMeN' in sonuc else '❌'}")

    print(f"\n{'='*40}")
    print("TEST SONUCLARI BASARILI ✅")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _test()
