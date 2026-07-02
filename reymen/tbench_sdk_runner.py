#!/usr/bin/env python3
"""Docker SDK-based hard task runner (bypasses MSYS path issues)"""
import docker
import os, io, tarfile, json, time

BASE = r"C:\Users\marko\Desktop\Reymen Proje\ReYMeN-Ajan\terminal-bench-benchmark\original-tasks"
RESULTS = r"C:\Users\marko\Desktop\Reymen Proje\ReYMeN-Ajan\.ReYMeN\reports\tbench-hard-sdk-results.json"

tasks = [
    ("chem-rf", "tbench-chemrf"),
    ("parallelize-graph", "tbench-parallelize"),
    ("port-compressor", "tbench-port"),
    ("gpt2-codegolf", "tbench-gpt2codegolf"),
    ("organization-json-generator", "tbench-orgjson"),
    ("cancel-async-tasks", "tbench-cancel-async"),
    ("configure-git-webserver", "tbench-gitweb"),
    ("find-official-code", "tbench-findcode"),
    ("fix-code-vulnerability", "tbench-fixvuln"),
    ("movie-helper", "tbench-movie"),
]

def make_tar(path, arc_prefix="/app/tests"):
    """Create tar stream from directory"""
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w') as tar:
        for root, dirs, files in os.walk(path):
            for fname in files:
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, path)
                arcname = f"{arc_prefix}/{rel}"
                with open(fpath, 'rb') as f:
                    info = tarfile.TarInfo(name=arcname)
                    info.size = os.path.getsize(fpath)
                    info.mode = 0o644
                    tar.addfile(info, f)
    stream.seek(0)
    return stream

client = docker.from_env()

all_results = []
for task_dir, img_name in tasks:
    print(f"\n=== {task_dir} ===")
    task_path = os.path.join(BASE, task_dir)
    
    # Read solution
    sol_path = os.path.join(task_path, "solution.sh")
    if not os.path.isfile(sol_path):
        print("  ❌ No solution.sh")
        continue
    
    with open(sol_path) as f:
        sol_content = f.read()
    
    result = {"task": task_dir, "solution": "❌", "tests": "❌"}
    
    try:
        # Create container
        container = client.containers.create(img_name, command="sleep 60")
        
        # Write solution.sh via tar
        s = io.BytesIO()
        with tarfile.open(fileobj=s, mode='w') as tar:
            info = tarfile.TarInfo(name="/tmp/sol.sh")
            info.size = len(sol_content)
            info.mode = 0o755
            tar.addfile(info, io.BytesIO(sol_content.encode()))
        s.seek(0)
        container.put_archive("/", s)
        
        # Start
        container.start()
        
        # Run solution
        exc, out = container.exec_run("bash /tmp/sol.sh")
        sol_ok = exc == 0
        print(f"  Solution: {'✅' if sol_ok else '❌'} (exit={exc})")
        if not sol_ok:
            print(f"    {out.decode()[:200]}")
        result["solution"] = "✅" if sol_ok else "❌"
        
        # Copy tests
        test_path = os.path.join(task_path, "tests")
        if os.path.isdir(test_path):
            container.put_archive("/", make_tar(test_path))
            
            # Install pytest + run tests
            exc, out = container.exec_run(
                "bash -c 'pip install pytest -q 2>/dev/null; python3 -m pytest /app/tests/ -v 2>&1'"
            )
            out_text = out.decode()
            
            if exc == 0:
                passed = out_text.count("PASSED")
                print(f"  Tests: ✅ ({passed} passed)")
                result["tests"] = f"✅ {passed}"
            elif exc == 1:
                passed = out_text.count("PASSED")
                failed = out_text.count("FAILED")
                print(f"  Tests: ⚠️ ({passed}/{passed+failed})")
                result["tests"] = f"⚠️ {passed}/{passed+failed}"
            else:
                print(f"  Tests: ❌ (exit={exc})")
                result["tests"] = f"❌ exit={exc}"
                err_text = out_text[:150].replace('\n',' ').strip()
                if err_text:
                    print(f"    {err_text}")
        else:
            print(f"  Tests: ❌ (no tests dir)")
        
        container.remove(force=True)
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        try:
            container.remove(force=True)
        except:
            pass
        result["error"] = str(e)[:100]
    
    all_results.append(result)

# Save
os.makedirs(os.path.dirname(RESULTS), exist_ok=True)
with open(RESULTS, "w") as f:
    json.dump(all_results, f, indent=2)

print(f"\n{'='*60}")
print("📊 HARD TASK RESULTS (Docker SDK)")
print(f"{'='*60}")
for r in all_results:
    print(f"  {r['task']:30s} Sol: {r['solution']:3s} Tests: {r['tests']}")
print(f"\n📄 Saved: {RESULTS}")
