#!/usr/bin/env python3
"""
ReYMeN Terminal-Bench Test Runner
Çözülen görevleri Docker container'ında doğrular.
Kullanım: python reymen/tbench_test_runner.py [görev_adı|all|report]
"""
import os, subprocess, json, sys, time

BASE = r"C:\Users\marko\Desktop\Reymen Proje\ReYMeN-Ajan\terminal-bench-benchmark\original-tasks"
IMAGE = "reymen-tbench-extended:latest"
RESULTS_FILE = r"C:\Users\marko\Desktop\Reymen Proje\ReYMeN-Ajan\.ReYMeN\reports\tbench-test-results.json"

# Çözüldüğü bilinen görevler
SOLVED = [
    "accelerate-maximal-square", "aimo-airline-departures", "analyze-access-logs",
    "assign-seats", "bank-trans-filter", "cobol-modernization", "count-call-stack",
    "countdown-game", "cpp-compatibility", "git-workflow-hack", "gomoku-planner",
    "grid-pattern-transform", "hello-world", "hydra-debug-slurm-mode", "ilp-solver",
    "jq-data-processing", "jsonl-aggregator", "jupyter-notebook-server", "log-summary",
    "mahjong-winninghand", "overfull-hbox", "pandas-sql-query", "processing-pipeline",
    "schedule-vacation", "security-vulhub-minio"
]

def run_in_docker(task_dir, cmd, timeout=120):
    """Run command inside Docker container with task mounted."""
    win_path = f"{BASE}\\{task_dir}"
    docker_cmd = f'docker run --rm -v "{win_path}:/app" {IMAGE} bash -c "{cmd}"'
    try:
        r = subprocess.run(docker_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:
        return -1, "", str(e)

def test_task(task_dir):
    """Run a single task's test suite."""
    # 1. Önce solution'ı çalıştır
    sol_sh = os.path.join(BASE, task_dir, "solution.sh")
    sol_py = os.path.join(BASE, task_dir, "solution.py")
    
    if os.path.isfile(sol_sh):
        rc, out, err = run_in_docker(task_dir, "bash /app/solution.sh", 60)
    elif os.path.isfile(sol_py):
        rc, out, err = run_in_docker(task_dir, "python3 /app/solution.py", 60)
    else:
        return {"task": task_dir, "status": "NO_SOLUTION", "error": ""}
    
    if rc != 0:
        return {"task": task_dir, "status": "SOLVE_FAILED", "error": err[:200]}
    
    # 2. Test'i çalıştır
    test_script = os.path.join(BASE, task_dir, "run-tests.sh")
    test_dir = os.path.join(BASE, task_dir, "tests")
    
    if os.path.isfile(test_script):
        # run-tests.sh içindeki TEST_DIR değişkenini /app/tests yap
        rc, out, err = run_in_docker(task_dir, 
            "export TEST_DIR=/app/tests && bash /app/run-tests.sh", 180)
    elif os.path.isdir(test_dir):
        # Doğrudan pytest çalıştır
        rc, out, err = run_in_docker(task_dir, 
            "cd /app && pip install pytest -q 2>/dev/null && pytest tests/ -v 2>&1", 180)
    else:
        return {"task": task_dir, "status": "NO_TESTS", "error": ""}
    
    test_passed = rc == 0
    return {
        "task": task_dir,
        "status": "PASSED" if test_passed else "TEST_FAILED",
        "error": "" if test_passed else (err[:300] if err else out[:300])
    }

def run_all():
    """Test all solved tasks."""
    results = []
    total = len(SOLVED)
    passed = 0
    
    print(f"\n{'='*60}")
    print(f"📊 Terminal-Bench Test Runner — {total} görev test ediliyor")
    print(f"{'='*60}\n")
    
    for i, task in enumerate(SOLVED):
        print(f"  [{i+1}/{total}] {task:40s} ", end="", flush=True)
        result = test_task(task)
        results.append(result)
        
        if result["status"] == "PASSED":
            passed += 1
            print("✅ PASSED")
        elif result["status"] == "NO_TESTS":
            print("⏭️  NO TESTS")
        elif result["status"] == "NO_SOLUTION":
            print("⏭️  NO SOLUTION")
        else:
            print(f"❌ {result['status']}")
    
    # Save results
    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"📈 SONUÇ: ✅ {passed}/{total} passed")
    
    if passed < total:
        print(f"\n❌ Başarısız Testler:")
        for r in results:
            if r["status"] not in ("PASSED", "NO_TESTS", "NO_SOLUTION"):
                print(f"  ❌ {r['task']}: {r['error'][:100]}")
    
    return results

def generate_report(results):
    """Generate Markdown report from test results."""
    passed = sum(1 for r in results if r["status"] == "PASSED")
    no_tests = sum(1 for r in results if r["status"] == "NO_TESTS")
    failed = sum(1 for r in results if r["status"] not in ("PASSED", "NO_TESTS", "NO_SOLUTION"))
    
    lines = []
    lines.append("# 🧪 ReYMeN Terminal-Bench Test Sonuçları")
    lines.append(f"**Tarih:** {time.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Docker İmajı:** {IMAGE}")
    lines.append("")
    lines.append("## 📊 Genel Durum")
    lines.append("")
    lines.append(f"| Metrik | Değer |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Toplam Görev | {len(results)} |")
    lines.append(f"| ✅ Test Geçti | {passed} |")
    lines.append(f"| ⏭️ Test Yok | {no_tests} |")
    lines.append(f"| ❌ Test Kaldı | {failed} |")
    lines.append(f"| Başarı Oranı | %{round(passed/len(results)*100) if results else 0} |")
    lines.append("")
    lines.append("## ✅ Geçen Testler")
    lines.append("")
    for r in results:
        if r["status"] == "PASSED":
            lines.append(f"- ✅ {r['task']}")
    lines.append("")
    lines.append("## ❌ Kalan Testler")
    lines.append("")
    for r in results:
        if r["status"] not in ("PASSED", "NO_TESTS", "NO_SOLUTION"):
            lines.append(f"- ❌ {r['task']}: `{r['error'][:80]}`")
    lines.append("")
    lines.append("## ⏭️ Atlananlar")
    lines.append("")
    for r in results:
        if r["status"] in ("NO_TESTS", "NO_SOLUTION"):
            lines.append(f"- ⏭️ {r['task']} ({r['status']})")
    
    return "\n".join(lines)

if __name__ == "__main__":
    results = run_all()
    report = generate_report(results)
    
    report_path = r"C:\Users\marko\Desktop\Reymen Proje\ReYMeN-Ajan\.ReYMeN\reports\tbench-test-report.md"
    with open(report_path, "w") as f:
        f.write(report)
    
    print(f"\n📄 Rapor: {report_path}")
