#!/usr/bin/env python3
"""Quick test 5 new hard tasks"""
import docker, os, io, tarfile, json

BASE = r"C:\Users\marko\Desktop\Reymen Proje\ReYMeN-Ajan\terminal-bench-benchmark\original-tasks"

tasks = [
    ("cancel-async-tasks", "tbench-cancel-async"),
    ("configure-git-webserver", "tbench-gitweb"),
    ("find-official-code", "tbench-findcode"),
    ("fix-code-vulnerability", "tbench-fixvuln"),
    ("movie-helper", "tbench-movie"),
]

client = docker.from_env()
results = []

for task_dir, img_name in tasks:
    print(f"\n=== {task_dir} ===")
    task_path = os.path.join(BASE, task_dir)
    
    with open(os.path.join(task_path, "solution.sh")) as f:
        sol_content = f.read()
    
    r = {"task": task_dir, "solution": "❌", "tests": "❌"}
    
    try:
        c = client.containers.create(img_name, command="sleep 60")
        
        # Copy solution
        s = io.BytesIO()
        with tarfile.open(fileobj=s, mode='w') as tar:
            info = tarfile.TarInfo(name="/tmp/sol.sh"); info.size = len(sol_content); info.mode = 0o755
            tar.addfile(info, io.BytesIO(sol_content.encode()))
        s.seek(0); c.put_archive("/", s); c.start()
        
        exc, out = c.exec_run("bash /tmp/sol.sh")
        r["solution"] = "✅" if exc == 0 else f"❌({exc})"
        print(f"  Solution: {r['solution']}")
        if exc != 0: print(f"    {out.decode()[:100]}")
        
        # Tests
        test_path = os.path.join(task_path, "tests")
        if os.path.isdir(test_path):
            ts = io.BytesIO()
            with tarfile.open(fileobj=ts, mode='w') as tar:
                for root, dirs, files in os.walk(test_path):
                    for fn in files:
                        fp = os.path.join(root, fn); rel = os.path.relpath(fp, test_path)
                        with open(fp, 'rb') as f:
                            info = tarfile.TarInfo(name=f"/app/tests/{rel}")
                            info.size = os.path.getsize(fp); info.mode = 0o644
                            tar.addfile(info, f)
            ts.seek(0); c.put_archive("/", ts)
            
            exc, out = c.exec_run("bash -c 'pip install pytest -q 2>/dev/null; python3 -m pytest /app/tests/ -v 2>&1'")
            ot = out.decode()
            if exc == 0:
                p = ot.count("PASSED"); r["tests"] = f"✅{p}"; print(f"  Tests: ✅ {p}")
            elif exc == 1:
                p = ot.count("PASSED"); f_ = ot.count("FAILED"); r["tests"] = f"⚠️{p}/{p+f_}"; print(f"  Tests: ⚠️ {p}/{p+f_}")
            else:
                r["tests"] = f"❌({exc})"; print(f"  Tests: ❌ ({exc})")
                first = ot.strip()[:80]; print(f"    {first}")
        else:
            print("  Tests: ❌ no tests dir")
        
        c.remove(force=True)
    except Exception as e:
        print(f"  ❌ {e}")
        try: c.remove(force=True)
        except: pass
        r["error"] = str(e)[:50]
    
    results.append(r)

print(f"\n{'='*50}")
for r in results:
    print(f"  {r['task']:30s} Sol: {r['solution']:6s} Tests: {r['tests']}")
