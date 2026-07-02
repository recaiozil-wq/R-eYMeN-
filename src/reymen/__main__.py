"""``python -m reymen`` için giriş noktası."""
import sys
from pathlib import Path

# Proje kökünü PATH'e ekle (reymen_launcher.py'nin yanı)
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))
from reymen_launcher import main

if __name__ == "__main__":
    raise SystemExit(main())
