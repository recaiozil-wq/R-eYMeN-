"""ReYMeN Web UI sunucu daemon'i — arka planda calisir."""
import os
import sys
import logging
logger = logging.getLogger(__name__)

# Proje kokunu sys.path'e ekle
_PROJE_KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJE_KOK not in sys.path:
    sys.path.insert(0, _PROJE_KOK)

import uvicorn

def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000

    try:
        from reymen.web_ui import app
        uvicorn.run(app, host=host, port=port, log_level="warning")
    except KeyboardInterrupt:
        logger.warning("[fix_01_sessiz_except] KeyboardInterrupt")
    except Exception as e:
        import traceback
        log_path = __file__ + ".log"
        with open(log_path, "w") as f:
            traceback.print_exc(file=f)
        sys.exit(1)

if __name__ == "__main__":
    main()
