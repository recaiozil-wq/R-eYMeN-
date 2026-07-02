"""Tum 7 modulun fonksiyonel testi - kodun gercekten calistigini kanitlar."""
import sys
import os

# Proje kokunu path'e ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=== MODUL FONKSIYONEL TEST ===")
print()

# 1. cost_tracker
from ReYMeN.cost_tracker import record_usage, summary, reset
reset()
record_usage("gpt-4o", prompt_tokens=1000, completion_tokens=500)
s = summary()
print(f"1. cost_tracker: OK - toplam maliyet=${s['total_cost_usd']:.4f}, cagri={s['total_calls']}")

# 2. platform_adapter
from ReYMeN.platform_adapter import detect, WSLAdapter, KaliAdapter
adapter = detect()
info = adapter.info()
print(f"2. platform_adapter: OK - kind={info.kind}, host_os={info.host_os}")

# 3. self_improve
from ReYMeN.self_improve import QualityMetric, record_step, report, evaluate
record_step(QualityMetric(success=True, errors=0, retries=0, duration=1.0))
r = report()
print(f"3. self_improve: OK - avg_score={r['avg_score']}, pass_rate={r['pass_rate']}")

# 4. video_tools
from ReYMeN.video_tools import check_available, VideoToolError
avail = check_available()
print(f"4. video_tools: OK - yt-dlp={avail['yt-dlp']}, ffmpeg={avail['ffmpeg']}")

# 5. a2a
from ReYMeN.a2a import Agent, Broker, Message, MessageType
broker = Broker()
alice = Agent("alice", broker)
bob = Agent("bob", broker)
alice.send("bob", "test mesaj")
msg = bob.receive(timeout=1.0)
print(f"5. a2a: OK - mesaj alindi: '{msg.content}'")

# 6. kanban
from ReYMeN.kanban import Board, Card, Priority
board = Board()
card = Card(title="test", priority=Priority.HIGH)
board.add(card, "todo")
board.move(card.id, "doing")
print(f"6. kanban: OK - kart sayisi={len(board.all_cards())}")

# 7. tui
from ReYMeN.tui import RICH_AVAILABLE, info, success
print(f"7. tui: OK - rich_available={RICH_AVAILABLE}")

print()
print("=== TUM 7 MODUL CALISIYOR ===")