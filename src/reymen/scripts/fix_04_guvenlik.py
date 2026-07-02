#!/usr/bin/env python3
"""
FIX 04 — Güvenlik Taraması (shell=False, credential, SQL, Bandit)
"""
import sys, json, time, shutil, subprocess, re
from pathlib import Path
from datetime import datetime
import logging
logger = logging.getLogger(__name__)
class C:
    RED="\033[91m"; YEL="\033[93m"; GRN="\033[92m"; BLU="\033[94m"; BOLD="\033[1m"; RESET="\033[0m"
def ok(m):   print(f"  {C.GRN}✅ {m}{C.RESET}")
def warn(m): print(f"  {C.YEL}⚠️  {m}{C.RESET}")
def err(m):  print(f"  {C.RED}❌ {m}{C.RESET}")
def hdr(t):  print(f"\n{C.BOLD}{C.BLU}{'═'*60}\n  {t}\n{'═'*60}{C.RESET}")

def py_files(kok):
    excl = {"__pycache__",".venv","venv","site-packages",".git","node_modules","bot_venv","chroma_db","skills","output","logs"}
    for f in kok.rglob("*.py"):
        parts = f.relative_to(kok).parts
        if not any(p in excl for p in parts): yield f

def main():
    kok = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(".").resolve()
    hdr(f"FIX 04 — Güvenlik Taraması\nKök: {kok}"); t0=time.time()
    rapor={"tarih":datetime.now().isoformat(),"kok":str(kok),"shell_true":[],"credential_leak":[],"sql_risk":[],"bandit":{},"ozet":{}}

    # shell=False
    hdr("1. shell=False Tespiti")
    for f in py_files(kok):
        if "test" in f.name.lower(): continue
        try:
            for i,line in enumerate(f.read_text(errors="ignore").splitlines(),1):
                if "shell=False" in line:
                    rapor["shell_true"].append(f"{f.relative_to(kok)}:{i}  {line.strip()[:80]}")
                    err(f"{f.relative_to(kok)}:{i}")
        except Exception as _e:
            pass  # log eklenecek
    if not rapor["shell_true"]: ok("shell=False bulunamadı")

    # Credential
    hdr("2. Hardcoded Credential")
    hp=re.compile(r"(api_key|secret|password|token|ACCESS_KEY)\s*=\s*['\"][^'\"]{8,}['\"]",re.I)
    for f in py_files(kok):
        try:
            for i,line in enumerate(f.read_text(errors="ignore").splitlines(),1):
                if hp.search(line) and "os.environ" not in line and "getenv" not in line:
                    rapor["credential_leak"].append(f"{f.relative_to(kok)}:{i}")
                    warn(f"{f.relative_to(kok)}:{i}")
        except Exception as _e:
            pass  # log eklenecek
    if not rapor["credential_leak"]: ok("Hardcoded credential yok")

    # SQL
    hdr("3. SQL Injection")
    sqlp=re.compile(r"(execute|executemany)\s*\(\s*[f\"'].*%s|f['\"].*SELECT.*\{",re.I)
    for f in py_files(kok):
        try:
            for i,line in enumerate(f.read_text(errors="ignore").splitlines(),1):
                if sqlp.search(line):
                    rapor["sql_risk"].append(f"{f.relative_to(kok)}:{i}")
                    warn(f"SQL: {f.relative_to(kok)}:{i}")
        except Exception as _e:
            pass  # log eklenecek
    if not rapor["sql_risk"]: ok("SQL riski yok")

    # Bandit
    hdr("4. Bandit")
    bandit=shutil.which("bandit")
    if bandit:
        try:
            r=subprocess.run([bandit,"-r",str(kok/"reymen"),"-ll","--quiet"],capture_output=True,text=True,timeout=60)
            out=r.stdout+r.stderr
            rapor["bandit"]["cikti"]=out[:2000]
            if "No issues identified" in out: ok("Bandit: sorun yok")
            else: warn("Bandit bulgu var — rapora bak")
        except Exception as e: warn(f"Bandit hata: {e}")
    else: warn("bandit yok — pip install bandit")

    rapor["ozet"]={"shell_true":len(rapor["shell_true"]),"credential":len(rapor["credential_leak"]),"sql_risk":len(rapor["sql_risk"])}
    rapor["sure"]=round(time.time()-t0,1)
    hdr("RAPOR")
    for k,v in rapor["ozet"].items(): print(f"  {k}: {C.RED if v else C.GRN}{v}{C.RESET}")
    rapor_yolu=kok/"fix_04_rapor.json"
    with open(rapor_yolu,"w") as fp: json.dump(rapor,fp,ensure_ascii=False,indent=2)
    ok(f"JSON rapor: {rapor_yolu}")

if __name__=="__main__": main()
