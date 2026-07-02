import logging

logger = logging.getLogger(__name__)
# -*- coding: utf-8 -*-
"""
planlayici.py — Planlama / alt-gorev bolme ve adaptif yeniden planlama.
Iyilestirmeler:
- yeniden_planla(): takilma durumunda strateji degistir
- tamamlanan_adim_isaretle(): ilerlemeyi takip et
- risk_degerlendirmesi(): riskli adimlar onceden isaretlenir
"""

PLAN_TALIMATI = """Sen bir gorev planlayicisisin. Verilen hedefi yurutülebilir
alt gorevlere bol. SADECE numarali liste dondur, baska aciklama yazma.
Hedef basitse tek satir yaz. En fazla 7 adim.

Kurallar:
- Her adim tek bir somut eylem olmali.
- Adimlar arasi bagimlilik sirasiyla gelmeli (once A, sonra B).
- Belirsiz adim yazma: "Bir seyler yap" degil "requests ile GET yap".
- Riskli adimlar icin adim basina [RISK] etiketi ekle.

Ornek:
Hedef: Bir web sitesinden veri cek ve dosyaya kaydet
1. requests ile https://example.com adresine GET yap
2. HTML'den ilgili veriyi BeautifulSoup ile ayikla
3. Ayiklanan veriyi veri.json dosyasina yaz
4. Dosyanin olusturuldugunu dogrula

Simdi su hedefi planla:
"""

YENIDEN_PLAN_TALIMATI = """Sen bir gorev planlayicisisin. Bir ajan hedefe ulasmaya
calisirken takildi. Simdi yeni bir strateji onermelisin.

Tamamlanan adimlar:
{tamamlanan}

Tikan nokta:
{hata}

Kalan hedef:
{kalan_hedef}

Yeni strateji icin alternatif adimlar yaz (numarali liste, en fazla 5 adim).
Ayni yaklasimi tekrarlama, farkli araclar veya yontemler oner.
"""

# ── Tree-of-Thought sabit metinleri ──────────────────────────────────────────

TOT_STRATEJI_TALIMATI = """Sen bir otonom ajan icin alternatif plan ureten bir planlayicisin.
Asagidaki hedef icin FARKLI bir strateji (yaklasim) uret.
Her stratejide 3-5 somut, numarali adim ver.
Strateji numarasi: {numara}
Strateji odagi: {odak}
Hedef: {hedef}
Sadece numarali adim listesi yaz, aciklama yazma."""

TOT_DEGERLENDIRME_TALIMATI = """Asagidaki {strateji_sayisi} plandan hangisi daha iyi?
Hedef: {hedef}

{planlar}

Sadece 'En iyi plan: N' yaz (N = plan numarasi). Hicbir aciklama ekleme."""


class Planlayici:
    # Tree-of-Thought icin strateji odaklari
    _TOT_ODAKLAR = [
        "en hizli ve dogrudan yol",
        "en guvenli, adim adim dogrulama",
        "alternatif araclar ve geri donus plani",
    ]

    def __init__(self, provider):
        self.provider = provider
        self._tamamlanan = []

    def plani_uret(self, hedef: str, tot: bool = False):
        """Hedefi alt gorev listesine bol.

        Args:
            hedef: Kullanici hedefi.
            tot:   True ise Tree-of-Thought ile 3 strateji uretip en iyisini sec.

        Returns:
            list[str]: Adim listesi. Model erisilemazse [hedef] doner.
        """
        # Basit sorgu bypass (3 kelime veya az) — provider cagrilmaz
        if tot:
            return self.tot_plani_uret(hedef)
        if len(hedef.split()) <= 3:
            return [hedef]
        try:
            cevap = self.provider.uret(PLAN_TALIMATI, [{"role": "user", "content": hedef}])
        except Exception:
            return [hedef]
        return self._satirlari_ayristir(cevap) or [hedef]

    def tot_plani_uret(self, hedef: str) -> list:
        """Tree-of-Thought planlama: 3 strateji uret, en iyisini sec.

        1. Her odak icin ayri strateji uret (paralel veya siralı).
        2. Modele hangi stratejinin daha iyi oldugunu sec.
        3. Secilen stratejinin adimlarini dondur.

        Hata durumunda standart planlama moduna geri duser.
        """
        try:
            return self._tot_yurut(hedef)
        except Exception:
            return self.plani_uret(hedef, tot=False)

    def _tot_yurut(self, hedef: str) -> list:
        stratejiler = []
        for i, odak in enumerate(self._TOT_ODAKLAR, 1):
            prompt = TOT_STRATEJI_TALIMATI.format(numara=i, odak=odak, hedef=hedef)
            try:
                cevap = self.provider.uret(prompt, [{"role": "user", "content": "Strateji:"}])
                adimlar = self._satirlari_ayristir(cevap)
                if adimlar:
                    stratejiler.append(adimlar)
                    print(f"[ToT] Strateji {i} ({odak[:30]}): {len(adimlar)} adim")
            except Exception:
                continue

        if not stratejiler:
            return self.plani_uret(hedef, tot=False)

        if len(stratejiler) == 1:
            return stratejiler[0]

        # Modele hangi stratejiyi secmeli sor
        planlar_metni = ""
        for i, adimlar in enumerate(stratejiler, 1):
            planlar_metni += f"\nPlan {i}:\n" + "\n".join(f"  {j}. {a}" for j, a in enumerate(adimlar, 1))

        degerlendirme_prompt = TOT_DEGERLENDIRME_TALIMATI.format(
            strateji_sayisi=len(stratejiler),
            hedef=hedef,
            planlar=planlar_metni,
        )
        try:
            karar = self.provider.uret(
                degerlendirme_prompt,
                [{"role": "user", "content": "En iyi plan:"}]
            )
            # "En iyi plan: N" formatini ayristir
            import re as _re
            m = _re.search(r'(\d+)', karar)
            if m:
                idx = int(m.group(1)) - 1
                if 0 <= idx < len(stratejiler):
                    print(f"[ToT] Secilen strateji: {idx + 1}")
                    return stratejiler[idx]
        except Exception as _e:
            logger.warning("[Planlayici] except Exception (L153): %s", Exception)
            pass

        # Hata varsa en kisa plani sec (muhtemelen en basit)
        return min(stratejiler, key=len)

    def yeniden_planla(self, hedef, tamamlanan_adimlar, hata_mesaji):
        """Takilma durumunda yeni strateji uret.

        Returns:
            list[str]: Yeni adim listesi. Bos donerse teslim ol sinyali.
        """
        tamamlanan_str = "\n".join(
            f"- {a}" for a in tamamlanan_adimlar
        ) or "(hic adim tamamlanmadi)"

        prompt = YENIDEN_PLAN_TALIMATI.format(
            tamamlanan=tamamlanan_str,
            hata=hata_mesaji[:300],
            kalan_hedef=hedef[:200],
        )
        try:
            cevap = self.provider.uret(prompt, [{"role": "user", "content": "Yeni strateji:"}])
        except Exception:
            return []
        adimlar = self._satirlari_ayristir(cevap)
        return adimlar

    def tamamlanan_adim_isaretle(self, adim):
        """Bir adimi tamamlandi olarak isaretle (ilerleme takibi icin)."""
        self._tamamlanan.append(adim)

    def tamamlananlar(self):
        return list(self._tamamlanan)

    def riskli_mi(self, adim):
        """Adim metninde [RISK] etiketi var mi kontrol et."""
        return "[RISK]" in adim.upper()

    def sifirla(self):
        self._tamamlanan = []

    def _satirlari_ayristir(self, cevap):
        adimlar = []
        for satir in cevap.splitlines():
            satir = satir.strip()
            if satir and (satir[0].isdigit() or satir.startswith("-")):
                temiz = satir.lstrip("0123456789.)- ").strip()
                if temiz:
                    adimlar.append(temiz)
        return adimlar


if __name__ == "__main__":
    class _Sahte:
        def uret(self, sp, m, **k):
            return "1. Siteyi ac\n2. Veriyi cek\n3. [RISK] Dosyaya yaz"

    p = Planlayici(_Sahte())
    plan = p.plani_uret("bir siteden veri cek")
    print("Plan:", plan)
    for a in plan:
        print(f"  Riskli mi? {p.riskli_mi(a):} — {a}")
    p.tamamlanan_adim_isaretle(plan[0])
    yeni = p.yeniden_planla("veri cek", p.tamamlananlar(), "requests.get timeout hatasi")
    print("Yeni plan:", yeni)
