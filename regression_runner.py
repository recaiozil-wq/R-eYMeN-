#!/usr/bin/env python3
"""
ReYMeN Regression Runner — Otomatik Regression Testi

Kullanım:
    python regression_runner.py           # Hızlı smoke (5 easy task)
    python regression_runner.py --full    # Tam regression (64 easy task)
    python regression_runner.py --status  # Son sonucu göster
    python regression_runner.py --watch   # Sürekli izle (cron dostu)

Çıktı: 
    - .ReYMeN/reports/regression-latest.json  (son sonuç)
    - .ReYMeN/reports/regression-history.json  (geçmiş)
"""

import json, os, subprocess, sys, time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SKOR_DB = os.path.join(BASE_DIR, ".ReYMeN", "reports", "tbench_skor_db.json")
REGRESSION_FILE = os.path.join(BASE_DIR, ".ReYMeN", "reports", "regression-latest.json")
HISTORY_FILE = os.path.join(BASE_DIR, ".ReYMeN", "reports", "regression-history.json")

SAMPLE_TASKS = [
    "hello-world", "countdown-game", "log-summary",
    "jsonl-aggregator", "pandas-etl"
]

def load_skor_db():
    """Mevcut skor DB'sini yükle."""
    if not os.path.isfile(SKOR_DB):
        return {}
    with open(SKOR_DB) as f:
        return json.load(f)

SAMPLE_TASKS_INLINE = [
    "hello-world", "countdown-game", "log-summary",
    "jsonl-aggregator", "pandas-sql-query"
]

def run_smoke_test():
    """Hızlı smoke test — Docker exec ile 5 easy task."""
    print(f"[{datetime.now().isoformat()}] 🧪 Smoke test başlıyor...")
    results = {}
    for task in SAMPLE_TASKS_INLINE:
        print(f"  → {task}...", end=" ")
        t0 = time.time()
        
        # Docker içinde bash solution.sh çalıştır
        result = subprocess.run(
            ["docker", "exec", "reymen-tbench-extended",
             "bash", "-c",
             f"cd /app && bash solution.sh 2>&1"],
            capture_output=True, text=True, timeout=120
        )
        
        elapsed = time.time() - t0
        success = result.returncode == 0
        results[task] = {
            "success": success,
            "elapsed_sec": round(elapsed, 1),
            "output": result.stdout[-200:] if result.stdout else result.stderr[-200:]
        }
        print(f"{'✅' if success else '❌'} ({elapsed:.1f}s)")
    
    return results

def run_full_regression():
    """Tam regression — tüm easy task'ler."""
    print(f"[{datetime.now().isoformat()}] 📊 Tam regression başlıyor...")
    
    result = subprocess.run(
        ["python3", "tbench_plan_recovery.py"],
        capture_output=True, text=True, timeout=7200  # 2 saat
    )
    
    return {
        "success": result.returncode == 0,
        "output": result.stdout[-500:],
        "returncode": result.returncode
    }

def compare_with_baseline(results):
    """Sonuçları baseline ile karşılaştır."""
    baseline = load_skor_db()
    
    solved_before = set(baseline.keys())
    solved_now = set(results.keys()) if isinstance(results, dict) else set()
    
    new_solved = solved_now - solved_before
    regressed = solved_before - solved_now
    
    return {
        "baseline_count": len(solved_before),
        "current_count": len(solved_now),
        "new_solved": list(new_solved),
        "regressed": list(regressed)
    }

def save_result(data):
    """Sonucu kaydet."""
    os.makedirs(os.path.dirname(REGRESSION_FILE), exist_ok=True)
    
    # Latest
    with open(REGRESSION_FILE, "w") as f:
        json.dump(data, f, indent=2)
    
    # History
    history = []
    if os.path.isfile(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            history = json.load(f)
    
    history.append(data)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history[-100:], f, indent=2)  # Son 100 kayıt
    
    print(f"  💾 Kaydedildi: {REGRESSION_FILE}")

def show_status():
    """Son regression durumunu göster."""
    if not os.path.isfile(REGRESSION_FILE):
        print("❌ Hiç regression çalıştırılmamış.")
        return
    
    with open(REGRESSION_FILE) as f:
        data = json.load(f)
    
    print(f"📋 Son Regression: {data.get('timestamp', 'bilinmiyor')}")
    print(f"  Tip: {data.get('type', '?')}")
    print(f"  Smoke: {data.get('smoke_success', '?')}")
    
    comparison = data.get('comparison', {})
    print(f"  Baseline: {comparison.get('baseline_count', 0)} task")
    print(f"  Şimdi: {comparison.get('current_count', 0)} task")
    if comparison.get('regressed'):
        print(f"  ⚠️ Regression: {comparison['regressed']}")
    if comparison.get('new_solved'):
        print(f"  🆕 Yeni çözüm: {comparison['new_solved']}")

if __name__ == "__main__":
    if "--status" in sys.argv:
        show_status()
        sys.exit(0)
    
    if "--full" in sys.argv:
        results = run_full_regression()
    else:
        results = run_smoke_test()
    
    comparison = compare_with_baseline(results)
    
    data = {
        "timestamp": datetime.now().isoformat(),
        "type": "full" if "--full" in sys.argv else "smoke",
        "smoke_success": all(r.get("success") for r in results.values()) if isinstance(results, dict) else results.get("success"),
        "results": results,
        "comparison": comparison
    }
    
    save_result(data)
    
    if comparison.get("regressed"):
        print(f"\n⚠️ REGRESSION TESPİT EDİLDİ: {comparison['regressed']}")
        sys.exit(1)
    else:
        print(f"\n✅ Regression yok — her şey stabil.")
        sys.exit(0)
