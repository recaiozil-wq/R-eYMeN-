#!/usr/bin/env python3
"""Self-improvement meta-loop: 672 iterations (7 days × 15 min)"""
import sys, os, logging

os.chdir(r'C:\Users\marko\Desktop\Reymen Proje\hermes_projesi')
sys.path.insert(0, os.getcwd())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

from src.reymen.cereyan.closed_learning_loop import ClosedLearningLoop

loop = ClosedLearningLoop(auto_index=True)
print(f"Baslangic: {loop.toplam_beceri_sayisi()} beceri")
print("672 iterasyon basliyor (7 gun = 15dk aralik)...")

loop.run_forever(cycle_hours=24, test_mode=True, max_test_iter=672)

print(f"\n✅ 672 iterasyon tamamlandi!")
print(f"Son durum: {loop.toplam_beceri_sayisi()} beceri")
