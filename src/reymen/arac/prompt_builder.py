# -*- coding: utf-8 -*-
"""prompt_builder.py — Gelişmiş Prompt İnşa Motoru.

Sistem prompt'unu, kullanıcı mesajlarını, hafıza, skill,
trajectory ve referansları birleştirerek LLM'e gönderilecek
eksiksiz prompt'u oluşturur.

Özellikler:
  - Çoklu kaynak birleştirme (SOUL, MEMORY, USER, skills, trajectory)
  - Dinamik araç listesi (motor tarafından kayıt)
  - Kanban durumu enjeksiyonu
  - Context references enjeksiyonu
  - Görev tipine göre prompt şablonu seçimi
  - Context penceresi yönetimi (token bütçesi)
  - OpenAI uyumlu mesaj listesi üretimi (mesaj_listesi / tur_mesaj_listesi)
  - Token analizi raporu
  - Adaptif detay seviyesi
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Sabit yollar
PROJE_KOK    = Path(__file__).parent.resolve()
SOUL_YOLU    = PROJE_KOK / ".ReYMeN" / "SOUL.md"
MEMORY_YOLU  = PROJE_KOK / ".ReYMeN" / "memories" / "MEMORY.md"
USER_YOLU    = PROJE_KOK / ".ReYMeN" / "memories" / "USER.md"
SKILLS_KLASOR= PROJE_KOK / ".ReYMeN" / "skills"
KANBAN_YOLU  = PROJE_KOK / ".ReYMeN" / "kanban" / "gorevler.json"

CTX_TOKEN_LIMITI = 8000

# ── Araç listesi (statik varsayılan — motor dinamik olarak günceller) ──
VARSAYILAN_ARACLAR = [
    'KOMUT_CALISTIR("kabuk komutu")     — shell komutu çalıştır',
    'PYTHON_CALISTIR("python kodu")     — python sandbox',
    'DOSYA_YAZ("dosya", "icerik")       — dosyaya yaz',
    'DOSYA_OKU("dosya")                 — dosyadan oku',
    'WEB_ARA("sorgu")                   — web araması',
    'TARAYICI_AC("url")                 — sayfayı aç ve oku',
    'EKRAN_TIKLA("yazi")                — ekranda bul ve tıkla',
    'EKRAN_OKU()                        — ekran metnini oku',
    'HAFIZA_ARA("sorgu")                — geçmiş deneyimlerde ara',
    'TELEGRAM_GONDER("mesaj")           — telegram bildirimi',
    'MAKRO_OYNAT("makro_adi")           — kayıtlı makro oynat',
    'GOREV_BITTI("kullaniciya_yanit")    — görevi bitir; argüman kullanıcıya gösterilir',
]

# ── Görev tipi şablonları ─────────────────────────────────────────────
TEMPLATELER = {
    "genel": {
        "aciklama": "Genel amaçlı görev",
        "vurgu": "Hedefe odaklan, adım adım ilerle.",
    },
    "dosya": {
        "aciklama": "Dosya işlemi",
        "vurgu": "Dosya yolunu doğrula, içeriği kontrol et, hata varsa raporla.",
    },
    "kod": {
        "aciklama": "Kod yazma/çalıştırma",
        "vurgu": "Önce PYTHON_CALISTIR ile test et, hata yoksa DOSYA_YAZ ile kaydet. try/except kullan.",
    },
    "web": {
        "aciklama": "Web işlemi",
        "vurgu": "Önce WEB_ARA ile bilgi topla, sonra TARAYICI_AC ile detaya in.",
    },
    "ekran": {
        "aciklama": "Ekran işlemi",
        "vurgu": "Önce EKRAN_OKU ile ekranı oku, sonra EKRAN_TIKLA ile işlem yap.",
    },
    "arastirma": {
        "aciklama": "Araştırma/analiz",
        "vurgu": "Önce plan yap, sonra adım adım araştır, en son rapor haline getir.",
    },
}

# ── ReAct format talimatı ─────────────────────────────────────────────
REACT_TALIMATI = """## Çalışma Döngüsü (ReAct)

Her turda şu sırayı takip et:
  DÜŞÜN: Hedefi analiz et, bir sonraki adımı planla.
  EYLEM: Yalnızca bir araç çağır.
  GÖZLEM: Araç sonucunu değerlendir, bir sonraki adıma geç.

Eylem formatı (tam bu şekilde kullan):
  ARAC_ADI("parametre1", "parametre2")

Özel durumlar:
  DUSUN("...") — sadece düşünce, eylem yok
  YARDIM_ISTE("ne bilmediğin") — belirsizlik varsa
  GOREV_BITTI("kullanıcıya verilecek yanıt") — tamamlandığında

ÖNEMLİ: GOREV_BITTI argümanı doğrudan kullanıcıya gösterilir.
  • Sohbet sorusuna yanıt → GOREV_BITTI("Merhaba! Nasıl yardımcı olabilirim?")
  • Görev tamamlandı  → GOREV_BITTI("Dosyayı oluşturdum: test.py — 42 satır.")
  • "Kullanıcıya tanıttım" / "görev tamam" gibi iç özet YAZMA.

Kurallar:
  • Her cevapta tam olarak BİR eylem veya GOREV_BITTI yaz.
  • Türkçe yanıt ver.
  • Asla: rm -rf, del /f, format, ../../ gibi yıkıcı/traversal işlem yapma."""


# ── Token yönetimi ────────────────────────────────────────────────────
def _token_say(metin: str) -> int:
    """4 karakter ≈ 1 token yaklaşımı."""
    return max(1, len(metin) // 4)


def _kes(metin: str, max_token: int, taraf: str = "bas") -> str:
    """Metni max_token sınırına kırp."""
    if _token_say(metin) <= max_token:
        return metin
    max_char = max_token * 4
    if taraf == "son":
        return "...\n" + metin[-max_char:]
    return metin[:max_char] + "\n...[kesildi]"


class PromptBuilder:
    """Gelişmiş prompt inşa motoru.

    Kullanım:
        pb = PromptBuilder()
        pb.araclar_kaydet(["DOSYA_OKU(...)", "WEB_ARA(...)"])
        sistem, mesajlar = pb.insa("hedef", gorev_tipi="dosya")

        # veya OpenAI uyumlu:
        mesaj_listesi = pb.mesaj_listesi("hedef")
    """

    def __init__(
        self,
        soul_dosyasi: Optional[Path] = None,
        max_token: int = CTX_TOKEN_LIMITI,
    ):
        self.soul_dosyasi = soul_dosyasi or SOUL_YOLU
        self.max_token    = max_token
        self._araclar: list[str] = []      # motor tarafından doldurulur

    # ── Araç kaydı ────────────────────────────────────────────────────

    def araclar_kaydet(self, araclar: list[str]):
        """Motor mevcut araç listesini bildirir."""
        self._araclar = list(araclar)

    def _araclar_metni(self) -> str:
        liste = self._araclar or VARSAYILAN_ARACLAR
        satirlar = ["## Kullanılabilir Araçlar"]
        for a in liste:
            satirlar.append(f"  • {a}")
        return "\n".join(satirlar)

    # ── Kaynak okuyucular ─────────────────────────────────────────────

    def _soul_oku(self) -> str:
        if self.soul_dosyasi and self.soul_dosyasi.exists():
            return self.soul_dosyasi.read_text(encoding="utf-8").strip()
        return "Ben ReYMeN, otonom bir yazılım ajanıyım."

    def _memory_oku(self, max_satir: int = 20) -> str:
        if not MEMORY_YOLU.exists():
            return ""
        satirlar = MEMORY_YOLU.read_text(encoding="utf-8").strip().split("\n")
        return "\n".join(satirlar[-max_satir:])

    def _user_oku(self, max_satir: int = 10) -> str:
        if not USER_YOLU.exists():
            return ""
        satirlar = USER_YOLU.read_text(encoding="utf-8").strip().split("\n")
        return "\n".join(satirlar[:max_satir])

    def _kanban_ozeti(self) -> str:
        if not KANBAN_YOLU.exists():
            return ""
        try:
            gorevler = json.loads(KANBAN_YOLU.read_text(encoding="utf-8"))
            aktif = [g for g in gorevler
                     if g.get("durum") in ("devam", "yapiliyor", "bekliyor")]
            if not aktif:
                return ""
            satirlar = ["[Kanban Aktif Görevler]"]
            for g in aktif[:4]:
                durum  = g.get("durum", "?").upper()
                baslik = g.get("baslik", g.get("hedef", "?"))[:55]
                satirlar.append(f"  [{durum}] {baslik}")
            return "\n".join(satirlar)
        except Exception:
            return ""

    def _skills_ozeti(self, limit: int = 6) -> str:
        if not SKILLS_KLASOR.exists():
            return ""
        dosyalar = list(SKILLS_KLASOR.rglob("SKILL.md"))[:limit]
        if not dosyalar:
            return ""
        satirlar = ["[Kullanılabilir Yetenekler]"]
        for s in dosyalar:
            ad  = s.parent.name
            kat = s.parent.parent.name
            satirlar.append(f"  - {kat}/{ad}")
        return "\n".join(satirlar)

    def _trajectory_gecmis(
        self,
        adimlar: Optional[list] = None,
        son_n: int = 4,
    ) -> str:
        """Doğrudan adımlar listesinden ya da dosyadan özet al."""
        if adimlar:
            son = adimlar[-son_n:]
            satirlar = ["[Son Adımlar]"]
            for a in son:
                t = a.get("tur", "?")
                e = str(a.get("eylem",  ""))[:65]
                g = str(a.get("gozlem", ""))[:65]
                satirlar.append(f"  [T{t}] {e} → {g}")
            return "\n".join(satirlar)

        # Dosya tabanlı fallback
        traj_dir = PROJE_KOK / ".ReYMeN" / "trajectories"
        if not traj_dir.exists():
            return ""
        dosyalar = sorted(traj_dir.glob("*.json"))[-3:]
        satirlar = []
        for d in dosyalar:
            try:
                veri = json.loads(d.read_text(encoding="utf-8"))
                satirlar.append(
                    f"  {veri['hedef'][:45]}: {veri['adim_sayisi']} adım"
                )
            except Exception as _e:
                logger.warning("[Trajectory gecmis] JSON: %s", _e)

        if satirlar:
            return "[Geçmiş Görevler]\n" + "\n".join(satirlar)
        return ""

    def _referanslar_metni(self, referanslar: Optional[list] = None) -> str:
        if not referanslar:
            return ""
        satirlar = ["[Bağlam Referansları]"]
        for r in referanslar[-3:]:
            etiket = r.get("etiket", "?")
            icerik = r.get("icerik", "")[:80]
            satirlar.append(f"  • {etiket}: {icerik}")
        return "\n".join(satirlar)

    # ── Ana prompt inşası ─────────────────────────────────────────────

    def insa(
        self,
        hedef: str,
        gorev_tipi: str = "genel",
        ek_bilgi: str = "",
        gecmis_konusma: Optional[list] = None,
        onceki_gozlem: str = "",
        tur: int = 1,
        adimlar: Optional[list] = None,
        referanslar: Optional[list] = None,
        max_token: Optional[int] = None,
    ) -> tuple[str, list]:
        """Tam prompt oluştur.

        Args:
            hedef:           Kullanıcı hedefi
            gorev_tipi:      "genel" | "dosya" | "kod" | "web" | "ekran" | "arastirma"
            ek_bilgi:        Ek bağlam
            gecmis_konusma:  Önceki mesajlar listesi
            onceki_gozlem:   Bir önceki turun gözlemi
            tur:             Mevcut tur numarası
            adimlar:         trajectory.adimlar (doğrudan enjeksiyon)
            referanslar:     context_references listesi
            max_token:       Context token sınırı (None = self.max_token)

        Returns:
            (sistem_prompt_str, openai_mesajlar_listesi)
        """
        limit = max_token or self.max_token
        template = TEMPLATELER.get(gorev_tipi, TEMPLATELER["genel"])

        # Bileşenleri topla
        soul       = self._soul_oku()
        memory     = self._memory_oku()
        user_bilgi = self._user_oku()
        skills     = self._skills_ozeti()
        kanban     = self._kanban_ozeti()
        traj       = self._trajectory_gecmis(adimlar)
        ref        = self._referanslar_metni(referanslar)

        parcalar: list[str] = [soul]

        if user_bilgi:
            parcalar.append(f"## Kullanıcı Profili\n{user_bilgi}")
        if memory:
            parcalar.append(f"## Geçmiş Deneyimler\n{memory}")
        if kanban:
            parcalar.append(kanban)
        if skills:
            parcalar.append(skills)
        if traj:
            parcalar.append(traj)
        if ref:
            parcalar.append(ref)

        parcalar.append(f"## Hedef\n{hedef}")

        if ek_bilgi:
            parcalar.append(f"## Ek Bilgi\n{ek_bilgi}")

        parcalar.append(f"## Yaklaşım ({template['aciklama']})\n{template['vurgu']}")
        parcalar.append(self._araclar_metni())
        parcalar.append(REACT_TALIMATI)

        if tur > 1 and onceki_gozlem:
            parcalar.append(
                f"## Mevcut Durum\nTur: {tur}\nGözlem: {_kes(onceki_gozlem, 150)}"
            )

        sistem_prompt = _kes("\n\n".join(p for p in parcalar if p), limit)

        # Mesaj listesi oluştur
        mesajlar: list[dict] = []
        if gecmis_konusma:
            harcanan = _token_say(sistem_prompt)
            for m in gecmis_konusma:
                m_token = _token_say(m.get("content", ""))
                if harcanan + m_token > limit:
                    break
                mesajlar.append(m)
                harcanan += m_token

        mesajlar.append({"role": "user", "content": hedef})
        return sistem_prompt, mesajlar

    # ── OpenAI uyumlu kısayollar ──────────────────────────────────────

    def sistem_prompt(
        self,
        hedef: str = "",
        gorev_tipi: str = "genel",
        adimlar: Optional[list] = None,
        referanslar: Optional[list] = None,
        ek_bilgi: str = "",
    ) -> str:
        """Yalnızca sistem promptunu döndür."""
        sistem, _ = self.insa(
            hedef=hedef,
            gorev_tipi=gorev_tipi,
            adimlar=adimlar,
            referanslar=referanslar,
            ek_bilgi=ek_bilgi,
        )
        return sistem

    def mesaj_listesi(
        self,
        hedef: str,
        gorev_tipi: str = "genel",
        adimlar: Optional[list] = None,
        referanslar: Optional[list] = None,
    ) -> list[dict]:
        """OpenAI/LM Studio uyumlu [system, user] mesaj listesi."""
        sistem = self.sistem_prompt(
            hedef=hedef, gorev_tipi=gorev_tipi,
            adimlar=adimlar, referanslar=referanslar,
        )
        return [
            {"role": "system", "content": sistem},
            {"role": "user",   "content": hedef},
        ]

    def tur_mesaj_listesi(
        self,
        hedef: str,
        tur: int,
        adimlar: Optional[list] = None,
        onceki_gozlem: str = "",
        gorev_tipi: str = "genel",
        referanslar: Optional[list] = None,
    ) -> list[dict]:
        """Devam eden tur için tam konuşma geçmişli mesaj listesi."""
        sistem = self.sistem_prompt(
            hedef=hedef, gorev_tipi=gorev_tipi,
            adimlar=adimlar, referanslar=referanslar,
        )
        mesajlar: list[dict] = [{"role": "system", "content": sistem}]

        # Son 6 adımı konuşma geçmişi olarak ekle
        if adimlar:
            for a in adimlar[-6:]:
                eylem  = str(a.get("eylem",  "")).strip()
                gozlem = str(a.get("gozlem", "")).strip()
                if eylem:
                    mesajlar.append({"role": "assistant", "content": eylem})
                if gozlem:
                    mesajlar.append({
                        "role": "user",
                        "content": f"Gözlem: {_kes(gozlem, 150)}",
                    })

        mesajlar.append({
            "role": "user",
            "content": self.tur_promptu(tur, onceki_gozlem=onceki_gozlem, hedef=hedef),
        })
        return mesajlar

    def tur_promptu(
        self,
        tur: int,
        dusunce: str = "",
        onceki_gozlem: str = "",
        hedef: str = "",
    ) -> str:
        """Ara tur kullanıcı mesajı."""
        satirlar = [f"## Tur {tur}"]
        if hedef:
            satirlar.append(f"Hedef: {hedef}")
        if onceki_gozlem:
            satirlar.append(f"Gözlem: {_kes(onceki_gozlem, 200)}")
        if dusunce:
            satirlar.append(f"Düşünce: {dusunce}")
        satirlar.append("\nŞimdi: Düşünce + Eylem üret.")
        return "\n".join(satirlar)

    # ── Token analizi ─────────────────────────────────────────────────

    def token_analizi(
        self,
        hedef: str = "",
        adimlar: Optional[list] = None,
    ) -> dict:
        """Prompt bileşenlerinin tahmini token maliyeti."""
        bilesenler = {
            "soul":          _token_say(self._soul_oku()),
            "memory":        _token_say(self._memory_oku()),
            "user_profil":   _token_say(self._user_oku()),
            "kanban":        _token_say(self._kanban_ozeti()),
            "skills":        _token_say(self._skills_ozeti()),
            "trajectory":    _token_say(self._trajectory_gecmis(adimlar)),
            "araclar":       _token_say(self._araclar_metni()),
            "react_talimati":_token_say(REACT_TALIMATI),
            "hedef":         _token_say(hedef),
        }
        bilesenler["toplam"] = sum(bilesenler.values())
        bilesenler["limit"]  = self.max_token
        bilesenler["asim"]   = max(0, bilesenler["toplam"] - self.max_token)
        return bilesenler


# ── Global singleton ──────────────────────────────────────────────────
_BUILDER: Optional[PromptBuilder] = None


def varsayilan_builder() -> PromptBuilder:
    global _BUILDER
    if _BUILDER is None:
        _BUILDER = PromptBuilder()
    return _BUILDER


def hizli_sistem_promptu(
    hedef: str,
    araclar: Optional[list[str]] = None,
    adimlar: Optional[list] = None,
) -> str:
    """Tek satırda sistem promptu oluştur."""
    b = varsayilan_builder()
    if araclar:
        b.araclar_kaydet(araclar)
    return b.sistem_prompt(hedef=hedef, adimlar=adimlar)


if __name__ == "__main__":
    pb = PromptBuilder()
    pb.araclar_kaydet([
        'DOSYA_OKU("yol")          — dosya içeriğini oku',
        'DOSYA_YAZ("yol","icerik") — dosyaya yaz',
        'WEB_ARA("sorgu")          — web araması',
        'KOMUT("cmd")              — shell komutu',
        'GOREV_BITTI("ozet")       — bitir',
    ])

    hedef = "Proje klasöründeki Python dosyalarını analiz et, özet rapor yaz"

    print("=== TOKEN ANALİZİ ===")
    for k, v in pb.token_analizi(hedef).items():
        print(f"  {k:<22} {v}")

    print("\n=== MESAJ LİSTESİ ===")
    for m in pb.mesaj_listesi(hedef, gorev_tipi="kod"):
        print(f"[{m['role']}] {m['content'][:120]}...\n")

    print("=== TUR MESAJ LİSTESİ (tur=3) ===")
    tur_mesajlari = pb.tur_mesaj_listesi(
        hedef, tur=3,
        adimlar=[
            {"tur": 1, "eylem": 'KOMUT("ls")',      "gozlem": "3 dosya"},
            {"tur": 2, "eylem": 'DOSYA_OKU("a.py")',"gozlem": "200 satir"},
        ],
    )
    print(f"{len(tur_mesajlari)} mesaj uretildi")
    for m in tur_mesajlari:
        print(f"  [{m['role']}] {m['content'][:80]}...")
