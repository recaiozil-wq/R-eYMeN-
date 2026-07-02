#!/usr/bin/env python3
"""Batch hard task runner — build + solution + test for all feasible tasks"""
import os, subprocess, json, time, re

BASE = r"C:\Users\marko\Desktop\Reymen Proje\ReYMeN-Ajan\terminal-bench-benchmark\original-tasks"
RESULTS = r"C:\Users\marko\Desktop\Reymen Proje\ReYMeN-Ajan\.ReYMeN\reports"

# Feasible hard tasks (no torch, no specialized env)
TASKS = [
    "cancel-async-tasks", "chem-property-targeting", "chem-rf",
    "circuit-fibsqrt", "configure-git-webserver", "extract-moves-from-video",
    "find-official-code", "fix-code-vulnerability", "gpt2-codegolf",
    "llm-inference-batching-scheduler", "model-extraction-relu-logits",
    "movie-helper", "neuron-to-jaxley-conversion",
    "organization-json-generator", "parallelize-graph",
    "password-recovery", "path-tracing", "path-tracing-reverse",
    "port-compressor", "rare-mineral-allocation",
    "regex-chess", "reverse-engineering",
    "stable-parallel-kmeans", "swe-bench-astropy-1", "swe-bench-astropy-2",
    "train-fasttext", "video-processing", "vul-flink",
    "word2vec-from-scratch", "write-compressor"
]

# Already tested
ALREADY_TESTED = {
    "stable-parallel-kmeans": {"build":"✅","solution":"✅","tests":"11/11","docker":"tbench-stable-kmeans"},
    "regex-chess": {"build":"✅","solution":"✅","tests":"timeout","docker":"tbench-regex-chess"},
    "password-recovery": {"build":"✅","solution":"✅","tests":"template","docker":"tbench-password-recovery"},
    "circuit-fibsqrt": {"build":"✅","solution":"✅","tests":"2/3","docker":"tbench-circuit"},
    "video-processing": {"build":"✅","solution":"✅","tests":"collection_error","docker":"tbench-video"},
}

def run_cmd(cmd, timeout=180):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:
        return -1, "", str(e)

def test_one(task):
    if task in ALREADY_TESTED:
        return ALREADY_TESTED[task]
    
    task_path = os.path.join(BASE, task)
    tag = f"tbench-hard-{task}"
    
    print(f"  🔨 Build {task}...", end=" ", flush=True)
    rc, out, err = run_cmd(f'docker build -t {tag} "{task_path}" 2>&1', timeout=180)
    if rc != 0:
        print(f"❌ BUILD FAILED")
        return {"build":"❌","solution":"","tests":"","docker":""}
    print(f"✅")
    
    # Run solution
    print(f"  🏃 Solution {task}...", end=" ", flush=True)
    rc, out, err = run_cmd(
        f'docker run --rm -v "{task_path}:/task" {tag} bash /task/solution.sh 2>&1', 
        timeout=300
    )
    if rc != 0 and rc != 127:
        print(f"❌ ({err[:50]})")
        sol_status = "❌"
    else:
        print(f"✅")
        sol_status = "✅"
    
    # Run tests
    print(f"  🧪 Test {task}...", end=" ", flush=True)
    rc, out, err = run_cmd(
        f'docker run --rm -v "{task_path}/tests:/app/tests" -v "{task_path}:/task" {tag} '
        f'bash -c "pip install pytest -q 2>/dev/null && python3 -m pytest tests/ -v 2>&1"',
        timeout=180
    )
    
    test_status = ""
    if rc == 0:
        passed = out.count("PASSED")
        print(f"✅ {passed} passed")
        test_status = f"✅ {passed}"
    elif rc == 1:
        passed = out.count("PASSED")
        failed = out.count("FAILED")
        print(f"⚠️ {passed} passed, {failed} failed")
        test_status = f"⚠️ {passed}/{passed+failed}"
    elif rc == -1:
        print(f"⏱️ timeout")
        test_status = "⏱️ timeout"
    else:
        print(f"❌")
        test_status = "❌"
    
    return {"build":"✅","solution":sol_status,"tests":test_status,"docker":tag}

print(f"\n{'='*70}")
print(f"  🚀 Batch Hard Task Runner — {len(TASKS)} tasks")
print(f"{'='*70}")

results = []
for i, task in enumerate(TASKS):
    print(f"\n[{i+1}/{len(TASKS)}] ", end="")
    r = test_one(task)
    r["task"] = task
    results.append(r)

# Summary table
print(f"\n\n{'='*70}")
print(f"📊 FINAL RESULTS")
print(f"{'='*70}")
print(f"{'#':>3} {'Task':35s} {'Build':6s} {'Sol':6s} {'Test':15s}")
print(f"{'-'*70}")
passed = 0
for i, r in enumerate(results):
    flag = "✅" if "✅" in r["tests"] else "⚠️" if "⚠️" in r["tests"] else "❌"
    if "✅" in r["tests"] and "❌" not in r["tests"]:
        passed += 1
    print(f"{i+1:3d} {r['task']:35s} {r['build']:6s} {r['solution']:6s} {r['tests']:15s}")

print(f"{'='*70}")
print(f"Total: {len(results)} | Build OK: {sum(1 for r in results if r['build']=='✅')} | Tests passing: {passed}")

# Save
os.makedirs(RESULTS, exist_ok=True)
with open(os.path.join(RESULTS, "tbench-hard-batch-results.json"), "w") as f:
    json.dump(results, f, indent=2)
print(f"\n📄 Saved: {RESULTS}/tbench-hard-batch-results.json")
