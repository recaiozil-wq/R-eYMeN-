#!/usr/bin/env python3
"""
MASTER — ReYMeN Tüm Fix'leri Çalıştır
Sırasıyla: Fix01 → Fix02 → Fix03 → Fix04 → Fix05
Her aşama sonrası rapor yazar, hata olursa durur.

Kullanım:
  python master_fix.py [proje_koku]
  python master_fix.py [proje_koku] --sadece 1,3,4
  python master_fix.py [proje_koku] --atla 3
"""
import sys, os, json, time, subprocess
from pathlib import Path
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

class C:
    RED="\033[91m"; YEL="\033[93m"; GRN="\033[92m"
    BLU="\033[94m"; BOLD="\033[1m"; RESET="\033[0m"

def hdr(t):
    print(f"\n{C.BOLD}{'█'*60}\n  {t}\n{'█'*60}{C.RESET}")
def ok(m):   print(f"  {C.GRN}✅ {m}{C.RESET}")
def warn(m): print(f"  {C.YEL}⚠️  {m}{C.RESET}")
def err(m):  print(f"  {C.RED}❌ {m}{C.RESET}")

FIXLER = [
    (1, "fix_01_sessiz_except.py", "Sessiz Except Temizleme (1,127 nokta)"),
    (2, "fix_02_all_ekle.py",      "__all__ Ekleme (121 init)"),
    (3, "fix_03_coverage.py",      "Coverage Kurulum & Test"),
    (4, "fix_04_guvenlik.py",      "Güvenlik Taraması"),
    (5, "fix_05_cli_bolme.py",     "cli.py Bölme Planı"),
]

def git_commit_al(kok: Path, mesaj: str) -> bool:
    try:
        subprocess.run(["git", "-C", str(kok), "add", "-A"], capture_output=True, timeout=30)
        r = subprocess.run(["git", "-C", str(kok), "commit", "-m", mesaj], capture_output=True, text=True, timeout=30)
        return r.returncode == 0
    except Exception:
        return False

def fix_calistir(fix_no, script_adi, aciklama, kok, script_dizin):
    script_yolu = script_dizin / script_adi
    if not script_yolu.exists():
        script_yolu = Path(__file__).parent / script_adi
    if not script_yolu.exists():
        return {"no": fix_no, "durum": "BULUNAMADI", "mesaj": str(script_yolu)}

    hdr(f"FIX {fix_no:02d} — {aciklama}")

    mesaj = f"pre-fix-{fix_no:02d}: {aciklama}"
    if git_commit_al(kok, mesaj): ok(f"Git commit: {mesaj}")
    else: warn("Git commit alınamadı (devam ediliyor)")

    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, str(script_yolu), str(kok)], timeout=300, text=True)
        sure = round(time.time() - t0, 1)
        basarili = r.returncode == 0
        if basarili: ok(f"FIX {fix_no:02d} tamamlandı ({sure}s)")
        else: err(f"FIX {fix_no:02d} hata kodu {r.returncode} ({sure}s)")

        rapor_yolu = kok / f"fix_{fix_no:02d}_rapor.json"
        rapor_icerik = {}
        if rapor_yolu.exists():
            try: rapor_icerik = json.loads(rapor_yolu.read_text(encoding="utf-8"))
            except Exception as _e:
                pass  # TODO: log ekle

        git_commit_al(kok, f"post-fix-{fix_no:02d}: {aciklama}")

        return {"no": fix_no, "aciklama": aciklama, "durum": "BASARILI" if basarili else "HATA",
                "return_code": r.returncode, "sure": sure, "rapor": rapor_icerik}
    except subprocess.TimeoutExpired:
        err(f"FIX {fix_no:02d} TIMEOUT (300s)")
        return {"no": fix_no, "aciklama": aciklama, "durum": "TIMEOUT", "sure": 300}
    except Exception as exc:
        err(f"FIX {fix_no:02d} istisnası: {exc}")
        return {"no": fix_no, "aciklama": aciklama, "durum": "HATA", "mesaj": str(exc)}

def main():
    kok = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(".").resolve()
    sadece = set(); atla = set()
    for i, arg in enumerate(sys.argv):
        if arg == "--sadece" and i+1 < len(sys.argv): sadece = {int(x) for x in sys.argv[i+1].split(",")}
        if arg == "--atla"   and i+1 < len(sys.argv): atla   = {int(x) for x in sys.argv[i+1].split(",")}

    hdr(f"MASTER — ReYMeN Fix Koşucusu\nKök: {kok}\nTarih: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    if sadece: print(f"  Sadece fix'ler: {sadece}")
    if atla:   print(f"  Atlananlar: {atla}")

    script_dizin = Path(__file__).parent
    t0 = time.time(); sonuclar = []

    for fix_no, script_adi, aciklama in FIXLER:
        if sadece and fix_no not in sadece:
            warn(f"FIX {fix_no:02d} — ATLANDI (--sadece)"); continue
        if fix_no in atla:
            warn(f"FIX {fix_no:02d} — ATLANDI (--atla)"); continue
        sonuc = fix_calistir(fix_no, script_adi, aciklama, kok, script_dizin)
        sonuclar.append(sonuc)
        if sonuc["durum"] == "HATA" and fix_no <= 2:
            err("FIX {fix_no:02d} kritik hata — durduruluyor! git checkout -- ."); break

    toplam_sure = round(time.time() - t0, 1)
    hdr("MASTER RAPOR")
    print(f"\n  {'Fix':<6} {'Durum':<12} {'Süre':<10} Açıklama\n  {'─'*60}")
    for s in sonuclar:
        renk = C.GRN if s["durum"]=="BASARILI" else (C.YEL if s["durum"]=="TIMEOUT" else C.RED)
        print(f"  {renk}FIX {s['no']:02d}  {s['durum']:<12} {str(s.get('sure','?'))+'s':<10} {s.get('aciklama','')}{C.RESET}")
    print(f"\n  Toplam süre: {toplam_sure}s")

    basarili = sum(1 for s in sonuclar if s["durum"]=="BASARILI")
    hata = sum(1 for s in sonuclar if s["durum"]=="HATA")
    timeout = sum(1 for s in sonuclar if s["durum"]=="TIMEOUT")
    print(f"  Başarılı: {C.GRN}{basarili}{C.RESET}  Hata: {C.RED}{hata}{C.RESET}  Timeout: {C.YEL}{timeout}{C.RESET}")

    for s in sonuclar:
        rapor = s.get("rapor", {})
        if rapor:
            print(f"\n  {C.BOLD}FIX {s['no']:02d} Özet:{C.RESET}")
            if s["no"]==1: print(f"    Düzeltme: {rapor.get('toplam_duzeltme','?')} sessiz except\n    Test geçen: {len(rapor.get('test_gecen',[]))}")
            elif s["no"]==2: print(f"    Eklenen __all__: {len(rapor.get('islenen',[]))}\n    Zaten vardı: {len(rapor.get('zaten_var',[]))}")
            elif s["no"]==4:
                for sev,sayi in rapor.get("ozet",{}).items():
                    renk = C.RED if sev in ("CRITICAL","HIGH") else C.YEL
                    print(f"    {renk}{sev}: {sayi}{C.RESET}")

    master_rapor = {"tarih": datetime.now().isoformat(), "kok": str(kok), "sonuclar": sonuclar,
                    "toplam_sure": toplam_sure, "ozet": {"basarili": basarili, "hata": hata, "timeout": timeout}}
    rapor_yolu = kok / "master_fix_rapor.json"
    with open(rapor_yolu, "w", encoding="utf-8") as fp:
        json.dump(master_rapor, fp, ensure_ascii=False, indent=2, default=str)
    print(f"\n  {C.GRN}✅ Master rapor: {rapor_yolu}{C.RESET}")
    if hata==0 and timeout==0: print(f"\n  {C.BOLD}{C.GRN}🎉 Tüm fix'ler başarıyla tamamlandı!{C.RESET}")
    else: print(f"\n  {C.YEL}⚠️  Bazı fix'lerde sorun var — raporları kontrol et{C.RESET}")

if __name__ == "__main__":
    main()
