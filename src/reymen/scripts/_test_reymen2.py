"""ReYMeN modül import testi"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
print("CWD:", os.getcwd())
print("SCRIPT DIR:", os.path.dirname(os.path.abspath(__file__)))
print("ReYMeN klasörü:", os.path.isdir("ReYMeN"))
print("init:", os.path.isfile("ReYMeN/__init__.py"))
try:
    import ReYMeN.cost_tracker
    print("✅ cost_tracker OK")
    import ReYMeN.a2a
    print("✅ a2a OK")
    import ReYMeN.kanban
    print("✅ kanban OK")
    import ReYMeN.platform_adapter
    print("✅ platform_adapter OK")
    import ReYMeN.self_improve
    print("✅ self_improve OK")
    import ReYMeN.tui
    print("✅ tui OK")
    import ReYMeN.video_tools
    print("✅ video_tools OK")
except Exception as e:
    print(f"❌ {e}")
    import traceback
    traceback.print_exc()
