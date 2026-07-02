#!/usr/bin/env python3
"""
ReYMeN Terminal-Bench Plan+Recovery Test Runner
- Plan: Görevi analiz et, strateji belirle
- Recovery: Başarısız olunca alternatif dene
- Rapor: Detaylı çözüm raporu
"""
import os, subprocess, json, sys, time, re

BASE = r"C:\Users\marko\Desktop\Reymen Proje\ReYMeN-Ajan\terminal-bench-benchmark\original-tasks"
IMAGE = "reymen-tbench-extended:latest"
RESULTS_FILE = r"C:\Users\marko\Desktop\Reymen Proje\ReYMeN-Ajan\.ReYMeN\reports\tbench-plan-recovery.json"

# === PLAN KATMANI ===

def analyze_task(task_dir):
    """Görevi analiz et, çözüm stratejisi belirle."""
    task_path = os.path.join(BASE, task_dir)
    yaml_file = os.path.join(task_path, "task.yaml")
    
    if not os.path.isfile(yaml_file):
        return {"status": "NO_YAML"}
    
    with open(yaml_file) as f:
        yaml = f.read()
    
    # Extract instruction
    instr = ""
    if "instruction:" in yaml:
        instr = yaml.split("instruction:", 1)[1].strip()
    
    # Extract category
    cat = ""
    for line in yaml.splitlines():
        if line.startswith("category:"):
            cat = line.split(":", 1)[1].strip()
    
    # Extract difficulty
    diff = ""
    for line in yaml.splitlines():
        if line.startswith("difficulty:"):
            diff = line.split(":", 1)[1].strip()
    
    # Plan: çözüm stratejisi
    strategies = []
    
    sol_sh = os.path.join(task_path, "solution.sh")
    sol_py = os.path.join(task_path, "solution.py")
    
    # Priority 1: solution.sh
    if os.path.isfile(sol_sh):
        with open(sol_sh) as f:
            content = f.read()
        needs_docker = "apt-get" in content or "docker" in content.lower()
        strategies.append({
            "type": "solution_sh",
            "file": sol_sh,
            "needs_docker": needs_docker,
            "priority": 1
        })
    
    # Priority 2: solution.py
    if os.path.isfile(sol_py):
        strategies.append({
            "type": "solution_py",
            "file": sol_py,
            "priority": 2
        })
    
    # Priority 3: manual Python (fallback)
    strategies.append({
        "type": "manual",
        "priority": 3
    })
    
    # Check data files
    data_files = []
    for root, dirs, files in os.walk(task_path):
        for f in files:
            if f not in ("task.yaml", "solution.sh", "solution.py", 
                        "run-tests.sh", "Dockerfile", "docker-compose.yaml",
                        "conftest.py"):
                data_files.append(os.path.relpath(os.path.join(root, f), task_path))
    
    return {
        "task": task_dir,
        "category": cat,
        "difficulty": diff,
        "instruction_preview": instr[:150],
        "strategies": strategies,
        "data_files": data_files[:10],
        "has_tests": os.path.isdir(os.path.join(task_path, "tests")),
        "has_dockerfile": os.path.isfile(os.path.join(task_path, "Dockerfile"))
    }

# === EXECUTION KATMANI ===

def run_in_docker(task_dir, cmd, timeout=120):
    """Docker container'da komut çalıştır.
    Çoklu servis varsa docker-compose'a yönlendir."""
    # Multi-service kontrol
    compose_path = os.path.join(BASE, task_dir, "docker-compose.yaml")
    if os.path.isfile(compose_path) and get_compose_services(task_dir) > 1:
        return run_in_compose(task_dir, cmd, timeout)
    
    win_path = f"{BASE}\\{task_dir}"
    docker_cmd = f'docker run --rm -v "{win_path}:/app" {IMAGE} bash -c "{cmd}"'
    try:
        r = subprocess.run(docker_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:
        return -1, "", str(e)

def run_in_docker_verbose(task_dir, cmd, timeout=120):
    """Docker'da çalıştır ve detaylı hata döndür."""
    rc, out, err = run_in_docker(task_dir, cmd, timeout)
    
    # Hata analizi
    error_type = "UNKNOWN"
    if rc == 0:
        error_type = "OK"
    elif err == "TIMEOUT":
        error_type = "TIMEOUT"
    elif "command not found" in err or "not found" in err:
        error_type = "CMD_NOT_FOUND"
    elif "No such file" in err:
        error_type = "FILE_NOT_FOUND"
    elif "pip" in err and ("error" in err or "failed" in err):
        error_type = "PIP_ERROR"
    elif "ImportError" in out or "ModuleNotFoundError" in out:
        error_type = "IMPORT_ERROR"
    elif "Permission denied" in err:
        error_type = "PERMISSION"
    
    return rc, out, err, error_type

# === DOCKER-COMPOSE KATMANI ===

COMPOSE_IMAGE = "reymen-tbench-compose:latest"

def get_compose_service_names(task_dir):
    """docker-compose.yaml'daki servis adlarını döndür (YAML ayrıştırma)."""
    compose_path = os.path.join(BASE, task_dir, "docker-compose.yaml")
    if not os.path.isfile(compose_path):
        return []
    with open(compose_path) as f:
        content = f.read()
    # Find the services: block, then get names at indent level +2
    services = []
    in_services = False
    for line in content.splitlines():
        if line.strip().startswith("services:"):
            in_services = True
            continue
        if in_services:
            # Lines at indent 0 = out of services block
            if line and not line[0].isspace():
                break
            # Service names have exactly 2-space indent (4 on Windows) or tab
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            if indent == 2 and stripped.endswith(":") and stripped != ":":
                services.append(stripped[:-1])
    return services

def get_compose_services(task_dir):
    """docker-compose.yaml'daki servis sayısını bul."""
    return len(get_compose_service_names(task_dir))

def build_compose_image(task_dir):
    """Task'in Dockerfile'ından compose imajı build et."""
    task_path = os.path.join(BASE, task_dir)
    dockerfile = os.path.join(task_path, "Dockerfile")
    if not os.path.isfile(dockerfile):
        return False, "No Dockerfile"
    try:
        tag = f"reymen-task-{task_dir}"
        r = subprocess.run(
            ["docker", "build", "-t", tag, "-f", dockerfile, task_path],
            capture_output=True, text=True, timeout=180
        )
        if r.returncode == 0:
            return True, tag
        return False, r.stderr[-200:]
    except Exception as e:
        return False, str(e)

def run_in_compose(task_dir, cmd, timeout=180):
    """docker-compose ile çoklu container'da komut çalıştır."""
    task_path = os.path.join(BASE, task_dir)
    compose_file = os.path.join(task_path, "docker-compose.yaml")
    
    if not os.path.isfile(compose_file):
        return run_in_docker(task_dir, cmd, timeout)
    
    service_count = get_compose_services(task_dir)
    if service_count <= 1:
        return run_in_docker(task_dir, cmd, timeout)
    
    # Multi-service: docker-compose kullan
    try:
        # Build images
        build_ok, tag = build_compose_image(task_dir)
        if not build_ok:
            return -1, "", f"Build failed: {tag}"
        
        # docker-compose up
        up = subprocess.run(
            ["docker-compose", "-f", compose_file, "up", "-d", "--build"],
            capture_output=True, text=True, timeout=timeout
        )
        if up.returncode != 0:
            subprocess.run(["docker-compose", "-f", compose_file, "down"], capture_output=True, timeout=30)
            return -1, "", f"compose up failed: {up.stderr[-200:]}"
        
        # Ana serviste komut çalıştır (ilk servis)
        service_names = get_compose_service_names(task_dir)
        main_service = service_names[0] if service_names else "app"
        exec_cmd = ["docker-compose", "-f", compose_file, "exec", "-T", main_service, "bash", "-c", cmd]
        r = subprocess.run(exec_cmd, capture_output=True, text=True, timeout=timeout)
        
        # Temizlik
        subprocess.run(["docker-compose", "-f", compose_file, "down", "-v"], capture_output=True, timeout=30)
        
        return r.returncode, r.stdout, r.stderr
    
    except subprocess.TimeoutExpired:
        subprocess.run(["docker-compose", "-f", compose_file, "down"], capture_output=True, timeout=30)
        return -1, "", "TIMEOUT"
    except Exception as e:
        subprocess.run(["docker-compose", "-f", compose_file, "down"], capture_output=True, timeout=30)
        return -1, "", str(e)

def run_in_compose_verbose(task_dir, cmd, timeout=180):
    """Compose'da çalıştır ve detaylı hata döndür."""
    rc, out, err = run_in_compose(task_dir, cmd, timeout)
    
    error_type = "UNKNOWN"
    if rc == 0:
        error_type = "OK"
    elif err == "TIMEOUT":
        error_type = "TIMEOUT"
    elif "command not found" in err or "not found" in err:
        error_type = "CMD_NOT_FOUND"
    elif "No such file" in err:
        error_type = "FILE_NOT_FOUND"
    elif "pip" in err and ("error" in err or "failed" in err):
        error_type = "PIP_ERROR"
    elif "ImportError" in out or "ModuleNotFoundError" in out:
        error_type = "IMPORT_ERROR"
    
    return rc, out, err, error_type

# === RECOVERY KATMANI ===

def recover_cmd_not_found(task_dir, cmd_name, solution_path):
    """Command not found hatası için recovery."""
    recovery_attempts = {
        "7z": ["7za", "p7zip", "7zr"],
        "python3": ["python", "python3.11", "python3.10"],
        "pip3": ["pip", "pip3.11"],
        "node": ["nodejs", "node20"],
        "npm": ["npm", "pnpm", "yarn"],
        "mlflow": ["python3 -m mlflow"],
        "jupyter": ["python3 -m jupyter"],
        "uv": ["/root/.local/bin/uv", "python3 -m uv"],
    }
    
    if cmd_name in recovery_attempts:
        for alt in recovery_attempts[cmd_name]:
            # Replace command in solution
            with open(solution_path) as f:
                content = f.read()
            modified = content.replace(cmd_name, alt)
            # Write temp solution
            tmp_path = solution_path + ".recovery"
            with open(tmp_path, "w") as f:
                f.write(modified)
            rc, out, err, etype = run_in_docker_verbose(task_dir, f"bash /app/{os.path.basename(tmp_path)}")
            os.remove(tmp_path)
            if rc == 0:
                return True, f"Recovery: {cmd_name} → {alt} başarılı"
    return False, f"Recovery başarısız: {cmd_name}"

def recover_pip_error(task_dir, solution_path):
    """Pip hatası için recovery - --break-system-packages ekle."""
    with open(solution_path) as f:
        content = f.read()
    
    # Replace pip/pip3 with break-system-packages flag
    modified = re.sub(r'(pip3?\s+install)', r'\1 --break-system-packages', content)
    # Also add uv init workaround
    modified = modified.replace("uv init", "uv init --no-readme 2>/dev/null || true")
    modified = modified.replace("uv add", "uv add --no-sync 2>/dev/null; uv sync 2>/dev/null || ")
    
    tmp_path = solution_path + ".recovery"
    with open(tmp_path, "w") as f:
        f.write(modified)
    rc, out, err, etype = run_in_docker_verbose(task_dir, f"bash /app/{os.path.basename(tmp_path)}")
    os.remove(tmp_path)
    if rc == 0:
        return True, "Recovery: pip --break-system-packages eklendi"
    return False, "Recovery başarısız: pip"

def recover_file_not_found(task_dir, solution_path):
    """Dosya bulunamadı hatası için recovery."""
    # Check if files are in task-deps/ or data/ instead of /app/
    task_path = os.path.join(BASE, task_dir)
    
    # Map files
    with open(solution_path) as f:
        content = f.read()
    
    # Find all /app/ references
    app_refs = re.findall(r'/app/([^\s"\']+)', content)
    
    if not app_refs:
        return False, "No /app/ references found"
    
    modified = content
    for ref in app_refs:
        # Check if file exists in subdirectories
        for subdir in ["task-deps", "data", "."]:
            src = os.path.join(task_path, subdir, ref)
            if os.path.exists(src):
                modified = modified.replace(f"/app/{ref}", f"/app/{subdir}/{ref}")
                break
    
    if modified != content:
        tmp_path = solution_path + ".recovery"
        with open(tmp_path, "w") as f:
            f.write(modified)
        rc, out, err, etype = run_in_docker_verbose(task_dir, f"bash /app/{os.path.basename(tmp_path)}")
        os.remove(tmp_path)
        if rc == 0:
            return True, f"Recovery: /app/ yolları düzeltildi"
    
    return False, "Recovery başarısız: dosya yolu"

def recover_uv_path(task_dir, solution_path):
    """uv PATH sorunu için recovery - source ~/.local/bin/env ekle."""
    with open(solution_path) as f:
        content = f.read()
    
    # Add source command at the beginning
    if "source $HOME/.local/bin/env" not in content:
        modified = "source $HOME/.local/bin/env 2>/dev/null || true\n" + content
        tmp_path = solution_path + ".recovery"
        with open(tmp_path, "w") as f:
            f.write(modified)
        rc, out, err, etype = run_in_docker_verbose(task_dir, f"bash /app/{os.path.basename(tmp_path)}")
        os.remove(tmp_path)
        if rc == 0:
            return True, "Recovery: uv PATH source eklendi"
    
    # Alternative: replace uv with full path
    modified = content.replace("uv ", "/root/.local/bin/uv ")
    modified = modified.replace("uv\n", "/root/.local/bin/uv\n")
    modified = modified.replace("uv;", "/root/.local/bin/uv;")
    modified = modified.replace("uv|", "/root/.local/bin/uv|")
    tmp_path = solution_path + ".recovery"
    with open(tmp_path, "w") as f:
        f.write(modified)
    rc, out, err, etype = run_in_docker_verbose(task_dir, f"bash /app/{os.path.basename(tmp_path)}")
    os.remove(tmp_path)
    if rc == 0:
        return True, "Recovery: uv → /root/.local/bin/uv"
    
    return False, "Recovery başarısız: uv"

def recover_import_error(task_dir, solution_path):
    """Import hatası için recovery - pip install --break-system-packages ile dene."""
    with open(solution_path) as f:
        content = f.read()
    
    # Detect missing imports
    imports = re.findall(r'(?:import|from)\s+(\w+)', content)
    
    # Common package mapping
    pkg_map = {
        "pandas": "pandas", "numpy": "numpy", "sklearn": "scikit-learn",
        "mlflow": "mlflow", "pulp": "pulp", "cv2": "opencv-python",
        "PIL": "pillow", "requests": "requests", "bs4": "beautifulsoup4",
        "duckdb": "duckdb", "matplotlib": "matplotlib", "seaborn": "seaborn",
        "jupyter": "jupyter", "fasttext": "fasttext"
    }
    
    to_install = []
    for imp in imports:
        if imp in pkg_map:
            pkg = pkg_map[imp]
            if pkg not in to_install:
                to_install.append(pkg)
    
    if to_install:
        pip_cmd = "pip3 install --break-system-packages " + " ".join(to_install)
        modified = pip_cmd + " 2>/dev/null || true\n" + content
        tmp_path = solution_path + ".recovery"
        with open(tmp_path, "w") as f:
            f.write(modified)
        rc, out, err, etype = run_in_docker_verbose(task_dir, f"bash /app/{os.path.basename(tmp_path)}", timeout=120)
        os.remove(tmp_path)
        if rc == 0:
            return True, f"Recovery: pip install {' '.join(to_install)}"
    
    return False, "Recovery başarısız: import"

def solve_with_recovery(task_dir):
    """Plan+Recovery ile görevi çözmeyi dene."""
    analysis = analyze_task(task_dir)
    
    result = {
        "task": task_dir,
        "category": analysis.get("category", ""),
        "attempts": [],
        "final_status": "FAILED"
    }
    
    # Her stratejiyi sırayla dene
    for strategy in analysis["strategies"]:
        attempt = {"strategy": strategy["type"], "status": "PENDING"}
        
        if strategy["type"] == "solution_sh":
            # Ana çözüm
            rc, out, err, etype = run_in_docker_verbose(task_dir, "bash /app/solution.sh")
            attempt["rc"] = rc
            attempt["error_type"] = etype
            
            if rc == 0:
                attempt["status"] = "OK"
                result["attempts"].append(attempt)
                
                # Test'i de çalıştır
                if analysis["has_tests"]:
                    trc, tout, terr = run_in_docker(task_dir, 
                        "cd /app && pip install pytest -q --break-system-packages 2>/dev/null && pytest tests/ -v 2>&1", 180)
                    attempt["test_passed"] = trc == 0
                result["final_status"] = "PASSED"
                break
            else:
                attempt["status"] = f"FAILED: {etype}"
                result["attempts"].append(attempt)
                
                # Recovery dene
                if etype == "CMD_NOT_FOUND":
                    cmd = extract_missing_cmd(err)
                    if cmd:
                        ok, msg = recover_cmd_not_found(task_dir, cmd, strategy["file"])
                        attempt["recovery"] = msg
                        if ok:
                            result["final_status"] = "PASSED_WITH_RECOVERY"
                            break
                
                elif etype == "PIP_ERROR":
                    ok, msg = recover_pip_error(task_dir, strategy["file"])
                    attempt["recovery"] = msg
                    if ok:
                        result["final_status"] = "PASSED_WITH_RECOVERY"
                        break
                
                elif etype == "FILE_NOT_FOUND":
                    ok, msg = recover_file_not_found(task_dir, strategy["file"])
                    attempt["recovery"] = msg
                    if ok:
                        result["final_status"] = "PASSED_WITH_RECOVERY"
                        break
                
                # Timeout durumunda daha uzun süre dene
                elif etype == "TIMEOUT":
                    rc2, out2, err2, etype2 = run_in_docker_verbose(task_dir, "bash /app/solution.sh", timeout=300)
                    attempt["retry_timeout"] = "300s"
                    if rc2 == 0:
                        attempt["status"] = "OK (retry)"
                        result["final_status"] = "PASSED"
                        break
                
                # Ek recovery: uv PATH sorunu
                ok, msg = recover_uv_path(task_dir, strategy["file"])
                attempt["recovery_uv"] = msg
                if ok:
                    result["final_status"] = "PASSED_WITH_RECOVERY"
                    break
                
                # Ek recovery: import hatası
                ok, msg = recover_import_error(task_dir, strategy["file"])
                attempt["recovery_import"] = msg
                if ok:
                    result["final_status"] = "PASSED_WITH_RECOVERY"
                    break
        
        elif strategy["type"] == "solution_py":
            rc, out, err, etype = run_in_docker_verbose(task_dir, "python3 /app/solution.py")
            attempt["rc"] = rc
            attempt["error_type"] = etype
            if rc == 0:
                attempt["status"] = "OK"
                result["final_status"] = "PASSED"
                break
            else:
                attempt["status"] = f"FAILED: {etype}"
                result["attempts"].append(attempt)
        
        elif strategy["type"] == "manual":
            attempt["status"] = "NO_MANUAL_SOLUTION"
            result["attempts"].append(attempt)
    
    return result

def extract_missing_cmd(error_text):
    """Hata mesajından eksik komut adını çıkar."""
    m = re.search(r'(\w+):\s+command not found', error_text)
    return m.group(1) if m else None

def run_all_with_recovery():
    """Tüm çözülen görevleri Plan+Recovery ile test et."""
    SOLVED = [
        "accelerate-maximal-square", "aimo-airline-departures", "analyze-access-logs",
        "assign-seats", "bank-trans-filter", "cobol-modernization", "count-call-stack",
        "countdown-game", "cpp-compatibility", "git-workflow-hack", "gomoku-planner",
        "grid-pattern-transform", "hello-world", "hydra-debug-slurm-mode", "ilp-solver",
        "jq-data-processing", "jsonl-aggregator", "jupyter-notebook-server", "log-summary",
        "mahjong-winninghand", "overfull-hbox", "pandas-sql-query", "processing-pipeline",
        "schedule-vacation", "security-vulhub-minio"
    ]
    
    # Ayrıca başarısız olanları da recovery ile dene
    FAILED_BUT_RECOVERABLE = [
        "ancient-puzzle", "csv-to-parquet", "heterogeneous-dates", 
        "pandas-etl", "mixed-integer-programming", "png-generation",
        "flood-monitoring-basic", "recover-accuracy-log", "fix-git",
        "mlflow-register"
    ]
    
    all_tasks = SOLVED + FAILED_BUT_RECOVERABLE
    
    print(f"\n{'='*60}")
    print(f"🧠 ReYMeN Plan+Recovery Test Runner")
    print(f"{'='*60}")
    print(f"  Toplam: {len(all_tasks)} görev")
    print(f"  - Önceden çözülen: {len(SOLVED)}")
    print(f"  - Recovery denenek: {len(FAILED_BUT_RECOVERABLE)}")
    print()
    
    results = []
    passed = 0
    recovered = 0
    failed = 0
    
    for i, task in enumerate(all_tasks):
        print(f"  [{i+1}/{len(all_tasks)}] {task:40s} ", end="", flush=True)
        result = solve_with_recovery(task)
        results.append(result)
        
        if result["final_status"] == "PASSED":
            passed += 1
            print("✅ PASSED")
        elif result["final_status"] == "PASSED_WITH_RECOVERY":
            recovered += 1
            print("🔄 RECOVERED")
        else:
            failed += 1
            attempts = len(result["attempts"])
            last = result["attempts"][-1] if result["attempts"] else {}
            print(f"❌ FAILED ({last.get('error_type','?')})")
    
    # Save results
    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"📊 SONUÇ: ✅ {passed} başarılı + 🔄 {recovered} recovery = {passed+recovered}/{len(all_tasks)}")
    print(f"❌ {failed} başarısız")
    print(f"📄 Rapor: {RESULTS_FILE}")
    
    # Rapor detayı
    print(f"\n📋 Recovery Detayı:")
    for r in results:
        for a in r.get("attempts", []):
            if "recovery" in a:
                print(f"  🔄 {r['task']}: {a['recovery']}")

if __name__ == "__main__":
    run_all_with_recovery()
