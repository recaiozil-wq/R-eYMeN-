#!/usr/bin/env python3
"""
ReYMeN Proje Analiz & Rapor Scripti
Kullanım: python reymen_analiz.py [proje_klasoru]
Varsayılan: mevcut dizin (.)
"""
import os, sys, ast, re, json, time, subprocess, shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import logging
logger = logging.getLogger(__name__)

EXCLUDE = {"venv", ".venv", "__pycache__", "node_modules", ".git", "bot_venv", "ReYMeN-full-backup", "hermes-memory-backup", "hermes_full_backup", "chroma_db", "skills", "optional-skills", "output", "logs", "screenshots", "references", "docs", "assets", "scripts", "rl_observation", "website", "bot_venv"}

class C:
    RED = "\033[91m"; YEL = "\033[93m"; GRN = "\033[92m"
    BLU = "\033[94m"; CYN = "\033[96m"; BOLD = "\033[1m"; RESET = "\033[0m"

def hdr(t, ch="═", w=65):
    print(f"\n{C.BOLD}{C.CYN}{ch*w}{C.RESET}\n{C.BOLD}{C.CYN}  {t}{C.RESET}\n{C.BOLD}{C.CYN}{ch*w}{C.RESET}")
def sub(t): print(f"\n{C.BOLD}{C.BLU}  ▶ {t}{C.RESET}")
def ok(m):  print(f"  {C.GRN}✅ {m}{C.RESET}")
def warn(m): print(f"  {C.YEL}⚠️  {m}{C.RESET}")
def err(m):  print(f"  {C.RED}❌ {m}{C.RESET}")
def info(m): print(f"  {C.BLU}ℹ️  {m}{C.RESET}")
def row(l, v, c=C.RESET): print(f"  {C.BOLD}{l:<30}{C.RESET} {c}{v}{C.RESET}")

RAPOR = {"tarih": datetime.now().strftime("%Y-%m-%d %H:%M"), "asamalar": {}}
def kaydet(a, v): RAPOR["asamalar"][a] = v

def py_files(kok):
    """Generator: .py files excluding venv/cache dirs"""
    for f in kok.rglob("*.py"):
        parts = f.relative_to(kok).parts
        if not any(p in EXCLUDE for p in parts) and not any(p.startswith(".") and p not in {".git", ".github", ".vscode", ".ReYMeN"} for p in parts):
            yield f

# ─── AŞAMA 1 — PROFİL ───────────────────────
def asama1_profil(kok):
    hdr("AŞAMA 1 — PROJE PROFİLİ & DOSYA İNVENTERİ")
    t0 = time.time()
    katmanlar = ["cereyan","sistem","hafiza","arac","ag","guvenlik","windows","altin_kayitlar"]
    py_s = defaultdict(int); test_s = defaultdict(int)
    toplam_py=0; toplam_test=0; skill=0; buyuk=[]

    for f in py_files(kok):
        rel = f.relative_to(kok)
        try: n = len(f.read_text(encoding="utf-8",errors="ignore").splitlines())
        except: n=0
        buyuk.append((n,str(rel)))
        if "test" in f.name.lower() or (len(rel.parts)>1 and "test" in rel.parts[0].lower()):
            toplam_test+=1
            for k in katmanlar:
                if k in str(rel): test_s[k]+=1
        else:
            toplam_py+=1
            for k in katmanlar:
                if k in str(rel): py_s[k]+=1

    for f in kok.rglob("SKILL.md"):
        parts = f.relative_to(kok).parts
        if not any(p in EXCLUDE for p in parts): skill+=1
    buyuk.sort(reverse=True)
    top8 = buyuk[:8]

    sub("Genel Sayaçlar")
    row("Python dosyası (toplam)", str(toplam_py))
    row("Test dosyası", str(toplam_test))
    row("SKILL.md", str(skill))

    sub("Katman Dağılımı (.py)")
    for k in katmanlar:
        if py_s[k]: row(f"  {k}/", f"{py_s[k]} .py")

    sub("En Büyük 8 Dosya")
    riskler = {0:"🔴 KRİTİK",1:"🟠 Yüksek",2:"🟡 Orta"}
    for i,(n,yol) in enumerate(top8):
        r=riskler.get(i,"🟢 İyi")
        c=C.RED if i==0 else (C.YEL if i<3 else C.RESET)
        print(f"  {c}{i+1:>2}. {yol:<50} {n:>6} satır  {r}{C.RESET}")

    son_commit=""
    try:
        son_commit = subprocess.check_output(["git","-C",str(kok),"log","--oneline","-1"],stderr=subprocess.DEVNULL).decode().strip()
        ok(f"Son commit: {son_commit}")
    except: warn("Git repo bulunamadı veya commit yok.")

    sure=time.time()-t0
    ok(f"Aşama 1 tamamlandı ({sure:.1f}s)")
    v={"toplam_py":toplam_py,"toplam_test":toplam_test,"skill_sayisi":skill,"katman_py":dict(py_s),"top8":top8,"son_commit":son_commit,"sure":sure}
    kaydet("1_profil",v)
    return v

# ─── AŞAMA 2 — MİMARİ ───────────────────────
def asama2_mimari(kok):
    hdr("AŞAMA 2 — MİMARİ & SORUMLULUK ANALİZİ")
    t0=time.time()
    bulgular=[]

    for f in kok.rglob("cli.py"):
        n=len(f.read_text(encoding="utf-8",errors="ignore").splitlines())
        if n>5000:
            m=f"cli.py → {n} satır — 7 sorumluluk tek dosyada (KRİTİK)"
            err(m); bulgular.append({"seviye":"KRİTİK","mesaj":m,"dosya":str(f.relative_to(kok))})
        else: ok(f"cli.py → {n} satır (kabul edilebilir)")

    ep=list(kok.rglob("reymen_agent.py"))+list(kok.rglob("reymen_launcher.py"))
    if len(ep)>1:
        m=f"Çift entry point: {[str(e.name) for e in ep]}"
        warn(m); bulgular.append({"seviye":"ORTA","mesaj":m})
    elif len(ep)==1: ok(f"Tek entry point: {ep[0].name}")
    else: info("Entry point dosyası bulunamadı.")

    paralel=list(kok.parent.glob("hermes_projesi"))
    if paralel:
        m="Paralel repo bulundu: hermes_projesi → drift tehlikesi"
        warn(m); bulgular.append({"seviye":"YÜKSEK","mesaj":m})
    else: ok("Paralel hermes_projesi bulunamadı")

    eksik_all=[]
    for init in kok.rglob("__init__.py"):
        parts = init.relative_to(kok).parts
        if any(p in EXCLUDE for p in parts): continue
        c=init.read_text(encoding="utf-8",errors="ignore")
        if "__all__" not in c and len(c.strip())>10:
            eksik_all.append(str(init.relative_to(kok)))
    if eksik_all:
        warn(f"__all__ eksik: {len(eksik_all)} __init__.py")
        bulgular.append({"seviye":"DÜŞÜK","mesaj":f"__all__ eksik: {len(eksik_all)} init","liste":eksik_all[:10]})
    else: ok("Tüm __init__.py dosyalarında __all__ mevcut (veya boş)")

    eski_import=[]
    for f in py_files(kok):
        try:
            txt=f.read_text(encoding="utf-8",errors="ignore")
            if re.search(r"^import cereyan\b|^from cereyan\b",txt,re.MULTILINE):
                eski_import.append(str(f.relative_to(kok)))
        except Exception as _e:
            pass  # TODO: log ekle
    if eski_import:
        warn(f"Eski-format import: {len(eski_import)} dosya")
        bulgular.append({"seviye":"ORTA","mesaj":"Eski import","liste":eski_import[:10]})
    else: ok("Import düzeni temiz (from reymen.* formatı)")

    sure=time.time()-t0
    ok(f"Aşama 2 tamamlandı ({sure:.1f}s)")
    kaydet("2_mimari",{"bulgular":bulgular,"eksik_all_sayisi":len(eksik_all),"sure":sure})

# ─── AŞAMA 3 — KOD KALİTESİ ────────────────
def asama3_kalite(kok):
    hdr("AŞAMA 3 — KOD KALİTESİ (TYPE HINT & EXCEPT)")
    t0=time.time()
    type_s={}; sessiz=[]; top_fonk=0; tipli_fonk=0
    hedef=["motor.py","beyin.py","cli.py","once_hafiza.py","tool_registry.py","conversation_loop.py","run_agent.py","main.py"]

    sub("Type Hint Oranı")
    for dn in hedef:
        dosyalar=list(kok.rglob(dn))
        if not dosyalar: continue
        f=dosyalar[0]
        try: src=f.read_text(encoding="utf-8",errors="ignore"); tree=ast.parse(src)
        except SyntaxError: warn(f"{dn}: Syntax hatası"); continue
        ft=0; f_t=0
        for node in ast.walk(tree):
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                ft+=1
                if node.returns is not None or any(a.annotation for a in node.args.args): f_t+=1
        if ft==0: continue
        o=f_t/ft*100; top_fonk+=ft; tipli_fonk+=f_t
        type_s[dn]={"toplam":ft,"tipli":f_t,"oran":o}
        c=C.GRN if o>=60 else (C.YEL if o>=40 else C.RED)
        print(f"  {c}{dn:<35} %{o:>5.1f}  ({f_t}/{ft}){C.RESET}")

    go=(tipli_fonk/top_fonk*100) if top_fonk else 0
    row("Genel ortalama",f"%{go:.1f}",C.YEL if go<60 else C.GRN)

    sub("Sessiz Except Tespiti")
    for f in py_files(kok):
        if "test" in f.name.lower(): continue
        try: src=f.read_text(encoding="utf-8",errors="ignore"); tree=ast.parse(src)
        except: continue
        for node in ast.walk(tree):
            if isinstance(node,ast.ExceptHandler):
                body=node.body
                if all(isinstance(s,(ast.Pass,ast.Expr)) for s in body):
                    only_ellipsis=all(isinstance(s,ast.Expr) and isinstance(getattr(s,'value',None),ast.Constant) for s in body)
                    if only_ellipsis or all(isinstance(s,ast.Pass) for s in body):
                        sessiz.append(f"{f.relative_to(kok)}:{node.lineno}")

    if sessiz:
        err(f"Sessiz except bulundu: {len(sessiz)} adet")
        for s in sessiz[:10]: print(f"    {C.RED}{s}{C.RESET}")
        if len(sessiz)>10: print(f"    ... ve {len(sessiz)-10} tane daha")
    else: ok("Sessiz except YOK ✅")

    sure=time.time()-t0
    ok(f"Aşama 3 tamamlandı ({sure:.1f}s)")
    kaydet("3_kalite",{"type_sonuc":type_s,"genel_oran":go,"sessiz_except":sessiz,"sure":sure})

# ─── AŞAMA 4 — TEST ─────────────────────────
def asama4_test(kok):
    hdr("AŞAMA 4 — TEST ANALİZİ")
    t0=time.time()
    pty=shutil.which("pytest")
    if not pty:
        warn("pytest bulunamadı — sadece dosya sayımı")
        td=list(kok.rglob("test_*.py"))+list(kok.rglob("*_test.py"))
        row("Test dosyası",str(len(td)))
        kaydet("4_test",{"pytest_yok":True,"test_dosyasi":len(td)})
        return

    pignore = ["--ignore=venv","--ignore=.venv","--ignore=bot_venv","--ignore=skills","--ignore=output","--ignore=logs","--ignore=gateway","--ignore=plugins","--ignore=tui_gateway","--ignore=ReYMeN_cli","--ignore=hermes-memory-backup","--ignore=hermes_full_backup","--ignore=acp","--ignore=ReYMeN-full-backup","--ignore=dashboard","--ignore=desktop","--ignore=notion_writer","--ignore=providers","--ignore=packaging","--ignore=proxy","--ignore=processors","--ignore=acp_adapter","--ignore=cron","--ignore=apps","--ignore=rl_observation","--ignore=notion_writer","--ignore=chroma_db"]
    sub("pytest --collect-only")
    try:
        r=subprocess.run([pty,"--collect-only","-q","--tb=no"]+pignore,cwd=str(kok),capture_output=True,text=True,timeout=60)
        sat=[s for s in r.stdout.splitlines() if "::" in s]
        row("Toplanan test",str(len(sat)))
        sm=re.search(r"(\d+) skipped",r.stdout+r.stderr)
        if sm: warn(f"Skip: {sm.group(1)} test")
    except subprocess.TimeoutExpired:
        warn("pytest collect timeout (60s)"); sat=[]

    sub("pytest -x --tb=short")
    gec=basarisiz=0
    try:
        r2=subprocess.run([pty,"--tb=short","-q","--no-header"]+pignore,cwd=str(kok),capture_output=True,text=True,timeout=300)
        out=r2.stdout+r2.stderr
        mp=re.search(r"(\d+) passed",out); mf=re.search(r"(\d+) failed",out)
        gec=int(mp.group(1)) if mp else 0
        basarisiz=int(mf.group(1)) if mf else 0
        if basarisiz==0: ok(f"{gec} test geçti, 0 hata ✅")
        else:
            err(f"{gec} geçti, {basarisiz} BAŞARISIZ")
            for line in out.splitlines()[:20]: print(f"    {C.RED}{line}{C.RESET}")
    except subprocess.TimeoutExpired: warn("pytest timeout (120s)")

    sub("Coverage Kontrolü")
    cov=shutil.which("coverage")
    if cov:
        try:
            subprocess.run([cov,"run","-m","pytest","-q","--tb=no"]+pignore,cwd=str(kok),capture_output=True,text=True,timeout=180)
            rc=subprocess.run([cov,"report","--skip-covered"],cwd=str(kok),capture_output=True,text=True,timeout=30)
            print(rc.stdout[:2000])
        except Exception as e: warn(f"Coverage çalışmadı: {e}")
    else: warn("coverage yok — pip install pytest-cov önerilir")

    sure=time.time()-t0
    ok(f"Aşama 4 tamamlandı ({sure:.1f}s)")
    kaydet("4_test",{"gecen":gec,"basarisiz":basarisiz,"sure":sure})

# ─── AŞAMA 5 — GÜVENLİK ─────────────────────
def asama5_guvenlik(kok):
    hdr("AŞAMA 5 — GÜVENLİK TARAMASI")
    t0=time.time()
    bulgular=[]

    sub("shell=True Tespiti")
    sl=[]
    for f in py_files(kok):
        if "test" in f.name.lower(): continue
        try:
            src=f.read_text(encoding="utf-8",errors="ignore")
            for i,line in enumerate(src.splitlines(),1):
                if "shell=True" in line: sl.append(f"{f.relative_to(kok)}:{i}  →  {line.strip()[:80]}")
        except Exception as _e:
            pass  # TODO: log ekle
    if sl:
        for s in sl: err(s)
        bulgular.append({"seviye":"HIGH","konu":"shell=True","liste":sl})
    else: ok("shell=True bulunamadı ✅")

    sub("Credential Tarama")
    hp=re.compile(r"(api_key|secret|password|token|ACCESS_KEY)\s*=\s*['\"][^'\"]{8,}['\"]",re.IGNORECASE)
    leak=[]
    for f in py_files(kok):
        try:
            src=f.read_text(encoding="utf-8",errors="ignore")
            for i,line in enumerate(src.splitlines(),1):
                if hp.search(line) and "os.environ" not in line and "getenv" not in line:
                    leak.append(f"{f.relative_to(kok)}:{i}")
        except Exception as _e:
            pass  # TODO: log ekle
    if leak:
        for s in leak[:10]: warn(f"Olası credential: {s}")
        bulgular.append({"seviye":"HIGH","konu":"hardcoded_credential","liste":leak})
    else: ok("Hardcoded credential bulunamadı ✅")

    sub(".gitignore Kontrolü")
    gi=kok/".gitignore"
    if gi.exists():
        c=gi.read_text(encoding="utf-8",errors="ignore")
        if ".env" in c: ok(".gitignore içinde .env var ✅")
        else: warn(".gitignore var ama .env yok!")
    else: warn(".gitignore bulunamadı!")

    sub("SQL Injection Tarama")
    sqlp=re.compile(r"(execute|executemany)\s*\(\s*[f\"'].*%s|f['\"].*SELECT.*\{",re.IGNORECASE)
    sqlr=[]
    for f in py_files(kok):
        try:
            src=f.read_text(encoding="utf-8",errors="ignore")
            for i,line in enumerate(src.splitlines(),1):
                if sqlp.search(line): sqlr.append(f"{f.relative_to(kok)}:{i}")
        except Exception as _e:
            pass  # TODO: log ekle
    if sqlr:
        for s in sqlr[:5]: warn(f"SQL risk: {s}")
    else: ok("SQL injection riski bulunamadı ✅")

    sub("Bandit")
    bandit=shutil.which("bandit")
    if bandit:
        try:
            r=subprocess.run([bandit,"-r",str(kok/"reymen"),"-ll","--quiet"],capture_output=True,text=True,timeout=60)
            out=r.stdout+r.stderr
            if "No issues identified" in out: ok("Bandit: sorun yok ✅")
            else:
                for line in out.splitlines()[:30]:
                    if "Severity" in line or "Issue" in line: print(f"  {C.YEL}{line}{C.RESET}")
        except Exception as e: warn(f"Bandit çalışmadı: {e}")
    else: warn("bandit yok — pip install bandit önerilir")

    sure=time.time()-t0
    ok(f"Aşama 5 tamamlandı ({sure:.1f}s)")
    kaydet("5_guvenlik",{"bulgular":bulgular,"shell_true":sl,"sure":sure})
    return {"bulgular":bulgular}

# ─── AŞAMA 6 — SKILL & ÖZET ─────────────────
def asama6_skill_ve_sonuc(kok,profil):
    hdr("AŞAMA 6 — SKILL KÜTÜPHANESİ & GENEL SONUÇ")
    t0=time.time()
    sub("SKILL.md Analizi")
    tum_skill=[s for s in kok.rglob("SKILL.md") if not any(p in EXCLUDE for p in s.relative_to(kok).parts)]
    row("Toplam SKILL.md",str(len(tum_skill)))
    if len(tum_skill)>100:
        warn(f"{len(tum_skill)} SKILL.md fazla — sadece ReYMeN'e özgü olanlar tutulabilir")
    else: ok("Skill sayısı makul")

    hdr("📊 YÖNETİCİ ÖZETİ","═")
    a1=RAPOR["asamalar"].get("1_profil",{})
    a3=RAPOR["asamalar"].get("3_kalite",{})
    a4=RAPOR["asamalar"].get("4_test",{})
    a5=RAPOR["asamalar"].get("5_guvenlik",{})

    bf=a4.get("basarisiz",0); se=len(a3.get("sessiz_except",[])); st=len(a5.get("shell_true",[]))
    if bf==0 and se==0: row("✅ TEMİZ","Test 0 hata, sessiz except yok",C.GRN)
    if se>0: row("⚠️ ORTA",f"{se} sessiz except",C.YEL)
    if st>0: row("🔴 RİSKLİ",f"{st} adet shell=True",C.RED)

    print()
    row("Python dosyası",str(a1.get("toplam_py","?")))
    row("Test dosyası",str(a1.get("toplam_test","?")))
    row("Type hint oranı",f"%{a3.get('genel_oran',0):.1f}",C.YEL)
    row("SKILL.md toplam",str(len(tum_skill)))
    row("Test başarısız",str(bf),C.RED if bf else C.GRN)

    sub("Öncelikli 3 Aksiyon")
    print(f"""
  {C.BOLD}1. {C.RED}cli.py BÖLME{C.RESET} — 7 bloka göre 7 ayrı .py, cli_main dispatch
  {C.BOLD}2. {C.YEL}TEST COVERAGE{C.RESET} — pip install pytest-cov, pytest --cov=reymen
  {C.BOLD}3. {C.BLU}ÇİFT PROJE KONSOLİDASYONU{C.RESET} — hermes_projesi → ReYMeN-Ajan
""")
    sure=time.time()-t0
    ok(f"Aşama 6 tamamlandı ({sure:.1f}s)")
    kaydet("6_skill",{"toplam_skill":len(tum_skill),"sure":sure})

# ─── JSON KAYDET ─────────────────────────────
def raporu_kaydet(kok):
    cikti=kok/"reymen_analiz_raporu.json"
    try:
        with open(cikti,"w",encoding="utf-8") as fp: json.dump(RAPOR,fp,ensure_ascii=False,indent=2,default=str)
        hdr("RAPOR KAYDEDİLDİ"); ok(f"{cikti}")
    except Exception as e: warn(f"JSON kayıt hatası: {e}")

# ─── ANA ────────────────────────────────────
def main():
    kok=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(".").resolve()
    if not kok.exists(): print(f"{C.RED}HATA: {kok} bulunamadı{C.RESET}"); sys.exit(1)
    print(f"\n{C.BOLD}{C.CYN}ReYMeN Proje Analiz Scripti{C.RESET}")
    print(f"{C.BLU}Proje kökü: {kok}{C.RESET}")
    tb=time.time()
    p=asama1_profil(kok)
    asama2_mimari(kok)
    asama3_kalite(kok)
    asama4_test(kok)
    asama5_guvenlik(kok)
    asama6_skill_ve_sonuc(kok,p)
    raporu_kaydet(kok)
    print(f"\n{C.BOLD}{C.GRN}Toplam süre: {time.time()-tb:.1f}s{C.RESET}\n")

if __name__=="__main__": main()
