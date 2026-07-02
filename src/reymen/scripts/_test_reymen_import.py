import sys, os
sys.path.insert(0, r"C:\Users\marko\Desktop\Reymen Proje\ReYMeN-Ajan")
print("Path:", sys.path[0])
print("ReYMeN var:", os.path.isdir(os.path.join(sys.path[0], "ReYMeN")))
print("init var:", os.path.isfile(os.path.join(sys.path[0], "ReYMeN", "__init__.py")))
try:
    import ReYMeN.cost_tracker
    print("✅ OK")
except Exception as e:
    print(f"❌ {e}")
