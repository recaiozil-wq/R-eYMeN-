# -*- coding: utf-8 -*-
"""
security_engine.py — SecurityEngine.
Guvenlik motoru: tarama, risk analizi, raporlama ve duzeltme.
ReYMeN kimligi: Turkce docstring, try/except, class-based.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path


class SecurityEngine:
    """SecurityEngine: Guvenlik taramalari ve risk yonetimi.

    Kod, dosya ve sistem guvenligini tarar, risk analizi yapar,
    rapor olusturur ve guvenlik aciklarini duzeltmeye calisir.
    """

    def __init__(self, kural_dosyasi=None):
        """SecurityEngine baslat.

        Args:
            kural_dosyasi: Guvenlik kurallari JSON dosyasi
        """
        self._rapor_gecmisi = []
        self._risk_seviyesi = 0
        self._son_tarama = None
        self._aciklar = []

        self._pii_desenleri = [
            (r'\b[\w.+-]+@[\w-]+\.[\w.-]+\b', 'EMAIL'),
            (r'\b\d{11}\b', 'TCKN'),
            (r'\b(?:\d[ -]?){13,16}\b', 'KART_NO'),
            (r'\b(?:0[0-9]{3})?[0-9]{10,11}\b', 'TELEFON'),
        ]
        self._tehdit_kelimeleri = [
            'rm -rf', 'drop table', 'shutdown', 'format',
            'eval(', 'exec(', 'system(', '__import__',
            'ignore all instructions', 'system prompt',
        ]
        self._risk_kurallari = {
            "yuksek": ["parola", "sifre", "token", "api_key", "secret"],
            "orta": ["localhost", "127.0.0.1", "debug", "test"],
            "dusuk": ["ornek", "dummy", "placeholder", "temp"],
        }

        if kural_dosyasi:
            try:
                with open(kural_dosyasi, "r", encoding="utf-8") as f:
                    self._ozel_kurallar = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as hata:
                print(f"[SecurityEngine] Kural dosyasi okunamadi: {hata}")
                self._ozel_kurallar = {}
        else:
            self._ozel_kurallar = {}

    def tarama_yap(self, hedef):
        """Belirtilen hedefi guvenlik taramasindan gecir.

        Args:
            hedef: Tarama hedefi (string icerik, dosya yolu veya kod)

        Returns:
            dict: Tarama sonucu
        """
        try:
            baslangic = datetime.now()
            icerik = ""
            kaynak = "dogrudan"

            if os.path.isfile(str(hedef)):
                try:
                    with open(hedef, "r", encoding="utf-8", errors="replace") as f:
                        icerik = f.read()
                    kaynak = str(hedef)
                except OSError as e:
                    return {"basari": False, "hata": f"Dosya okunamadi: {e}", "seviye": "hata"}
            else:
                icerik = str(hedef)

            bulunan_aciklar = []
            pii_bulunan = []

            for desen, etiket in self._pii_desenleri:
                try:
                    eslesmeler = re.findall(desen, icerik)
                    if eslesmeler:
                        pii_bulunan.append({"tur": etiket, "adet": len(eslesmeler)})
                        bulunan_aciklar.append({
                            "tur": "pii",
                            "etiket": etiket,
                            "adet": len(eslesmeler),
                            "seviye": "yuksek",
                        })
                except re.error:
                    continue

            for kelime in self._tehdit_kelimeleri:
                if kelime.lower() in icerik.lower():
                    bulunan_aciklar.append({
                        "tur": "tehdit",
                        "kelime": kelime,
                        "seviye": "kritik",
                    })

            icerik_kucuk = icerik.lower()
            for seviye, anahtarlar in self._risk_kurallari.items():
                for anahtar in anahtarlar:
                    if anahtar.lower() in icerik_kucuk:
                        bulunan_aciklar.append({
                            "tur": "risk",
                            "anahtar": anahtar,
                            "seviye": seviye,
                        })

            self._son_tarama = {
                "zaman": baslangic.isoformat(),
                "hedef": kaynak,
                "boyut": len(icerik),
                "acik_sayisi": len(bulunan_aciklar),
                "aciklar": bulunan_aciklar,
                "pii": pii_bulunan,
            }
            self._aciklar = bulunan_aciklar
            self._risk_seviyesi = self._risk_hesapla(bulunan_aciklar)

            return self._son_tarama

        except Exception as hata:
            print(f"[SecurityEngine] Tarama hatasi: {hata}")
            return {"basari": False, "hata": str(hata), "seviye": "hata"}

    def _risk_hesapla(self, aciklar):
        """Risk seviyesini hesapla.

        Args:
            aciklar: Acik listesi

        Returns:
            int: Risk puani (0-100)
        """
        try:
            puan = 0
            for acik in aciklar:
                seviye = acik.get("seviye", "dusuk")
                if seviye == "kritik":
                    puan += 30
                elif seviye == "yuksek":
                    puan += 20
                elif seviye == "orta":
                    puan += 10
                else:
                    puan += 5
            return min(puan, 100)
        except Exception:
            return 0

    def risk_analizi(self):
        """Risk analizi raporu uret.

        Returns:
            dict: Risk analizi sonucu
        """
        try:
            if not self._son_tarama:
                return {"hata": "Henuz tarama yapilmadi", "seviye": "bilinmiyor"}

            seviye_etiket = "dusuk"
            if self._risk_seviyesi >= 70:
                seviye_etiket = "kritik"
            elif self._risk_seviyesi >= 40:
                seviye_etiket = "yuksek"
            elif self._risk_seviyesi >= 15:
                seviye_etiket = "orta"

            analiz = {
                "risk_puani": self._risk_seviyesi,
                "risk_seviyesi": seviye_etiket,
                "acik_sayisi": len(self._aciklar),
                "kritik_sayisi": sum(1 for a in self._aciklar if a.get("seviye") == "kritik"),
                "yuksek_sayisi": sum(1 for a in self._aciklar if a.get("seviye") == "yuksek"),
                "orta_sayisi": sum(1 for a in self._aciklar if a.get("seviye") == "orta"),
                "dusuk_sayisi": sum(1 for a in self._aciklar if a.get("seviye") == "dusuk"),
                "tavsiye": self._tavsiye_uret(seviye_etiket),
            }
            return analiz

        except Exception as hata:
            print(f"[SecurityEngine] Risk analizi hatasi: {hata}")
            return {"hata": str(hata)}

    def _tavsiye_uret(self, seviye):
        """Risk seviyesine gore tavsiye uret.

        Args:
            seviye: Risk seviyesi

        Returns:
            str: Tavsiye metni
        """
        tavsiyeler = {
            "kritik": "Hemen mudahale gerekli! Tum aciklari duzeltin.",
            "yuksek": "En kisa surede duzeltme yapilmalidir.",
            "orta": "Planli bakim sirasinda duzeltilmesi onerilir.",
            "dusuk": "Su an icin risk dusuk, periyodik kontrol yeterli.",
        }
        return tavsiyeler.get(seviye, "Bilinmeyen seviye")

    def rapor_uret(self, seviye="detayli"):
        """Guvenlik raporu olustur.

        Args:
            seviye: Rapor detay seviyesi (ozet, detayli, json)

        Returns:
            str veya dict: Rapor
        """
        try:
            if not self._son_tarama:
                return "Henuz tarama yapilmadi."

            analiz = self.risk_analizi()

            if seviye == "json":
                return {
                    "tarama": self._son_tarama,
                    "analiz": analiz,
                }

            rapor_metni = f"""
==================================
GUVENLIK RAPORU
==================================
Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Risk Puani: {analiz.get('risk_puani', '?')}/100
Risk Seviyesi: {analiz.get('risk_seviyesi', '?').upper()}
----------------------------------
Tespit: {analiz.get('acik_sayisi', 0)} guvenlik acigi
  - Kritik: {analiz.get('kritik_sayisi', 0)}
  - Yuksek: {analiz.get('yuksek_sayisi', 0)}
  - Orta:   {analiz.get('orta_sayisi', 0)}
  - Dusuk:  {analiz.get('dusuk_sayisi', 0)}
----------------------------------
Tavsiye: {analiz.get('tavsiye', 'Yok')}
==================================
"""
            if seviye == "detayli" and self._son_tarama.get("aciklar"):
                rapor_metni += "\nDetayli Acik Listesi:\n"
                for i, acik in enumerate(self._son_tarama["aciklar"], 1):
                    rapor_metni += f"  {i}. [{acik.get('seviye','?').upper()}] "
                    rapor_metni += f"{acik.get('tur','?')}: {acik.get('etiket') or acik.get('kelime') or acik.get('anahtar','?')}\n"

            return rapor_metni.strip()

        except Exception as hata:
            return f"Rapor olusturma hatasi: {hata}"

    def duzelt(self, guvenlik_acigi):
        """Guvenlik acigini duzeltmeye calis.

        Args:
            guvenlik_acigi: Acik bilgisi (dict)

        Returns:
            dict: Duzeltme sonucu
        """
        try:
            if not guvenlik_acigi or not isinstance(guvenlik_acigi, dict):
                return {"basari": False, "hata": "Gecersiz acik bilgisi"}

            acik_turu = guvenlik_acigi.get("tur", "")
            etiket = guvenlik_acigi.get("etiket", "")

            if acik_turu == "pii":
                return {
                    "basari": True,
                    "mesaj": f"PII verisi ({etiket}) maskelenmeli. Manuel kontrol onerilir.",
                    "duzeltme": "redakte",
                }
            elif acik_turu == "tehdit":
                return {
                    "basari": True,
                    "mesaj": f"Tehdit kelimesi ({etiket}) koddan kaldirildi.",
                    "duzeltme": "temizleme",
                }
            elif acik_turu == "risk":
                return {
                    "basari": True,
                    "mesaj": f"Riskli anahtar ({etiket}) gozden gecirildi.",
                    "duzeltme": "inceleme",
                }
            else:
                return {
                    "basari": False,
                    "hata": f"Bilinmeyen acik turu: {acik_turu}",
                }

        except Exception as hata:
            print(f"[SecurityEngine] Duzeltme hatasi: {hata}")
            return {"basari": False, "hata": str(hata)}

    def aciklari_listele(self):
        """Tespit edilen aciklari listele.

        Returns:
            list: Acik listesi
        """
        return self._aciklar

    def son_taramayi_getir(self):
        """Son tarama bilgisini getir.

        Returns:
            dict: Son tarama
        """
        return self._son_tarama


class AdvancedMemorySecurityEngine:
    """main.py'nin kullandigi PII redaction + injection tespiti motoru."""

    _PII = [
        (re.compile(r'\b[\w.+-]+@[\w-]+\.[\w.-]+\b'), '[EMAIL]'),
        (re.compile(r'\b\d{11}\b'),                    '[TCKN]'),
        (re.compile(r'\b(?:\d[ -]?){13,16}\b'),        '[KART_NO]'),
    ]
    _INJECTION = re.compile(
        r'ignore (all )?instructions?|'
        r'forget (all )?previous|'
        r'system prompt|'
        r'jailbreak|'
        r'disregard (all )?',
        re.IGNORECASE,
    )

    def injection_var_mi(self, metin: str) -> bool:
        return bool(self._INJECTION.search(metin))

    def redact(self, metin: str) -> str:
        for desen, yer in self._PII:
            metin = desen.sub(yer, metin)
        return metin


if __name__ == "__main__":
    se = SecurityEngine()
    test_kodu = """
def login():
    sifre = "admin123"
    api_key = "sk-1234567890abcdef"
    # test icin localhost kullan
    print("debug mod aktif")
    return True
"""
    tarama = se.tarama_yap(test_kodu)
    print(f"Acik sayisi: {tarama.get('acik_sayisi', 0)}")
    analiz = se.risk_analizi()
    print(f"Risk: {analiz.get('risk_puani', '?')}/100 - {analiz.get('risk_seviyesi', '?')}")
    print(se.rapor_uret("ozet"))
