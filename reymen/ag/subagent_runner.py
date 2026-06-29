# -*- coding: utf-8 -*-
"""
subagent_runner.py — Alt-ajan çalıştırıcı.
DelegationManager tarafından subprocess olarak çağrılır.
Stdin'den JSON {goal, context} alır, stdout'a JSON {status, result} yazar.
"""
import json
import sys
import time
import traceback


def run(goal: str, context: str = "") -> dict:
    """
    Verilen goal/context ile alt-ajan görevini çalıştır.
    Basit bir LLM benzeri yanıt üretir — gerçek ortamda bu bir AI çağrısı olur.
    """
    try:
        # Görevi işle
        baslik = goal.strip()
        if not baslik:
            return {"status": "error", "result": "Boş hedef gönderildi"}

        lines = baslik.split("\n")
        adim_sayisi = len([l for l in lines if l.strip()])

        sonuc_parts = [
            f"[SubAgent] Görev tamamlandı: {baslik[:120]}",
            f"  Bağlam: {context[:200] if context else '(yok)'}",
            f"  İşlenen adım sayısı: {adim_sayisi or 1}",
        ]

        # Görev türüne göre basit bir çıktı oluştur
        goal_lower = baslik.lower()
        if "ara" in goal_lower or "search" in goal_lower or "bul" in goal_lower:
            sonuc_parts.append(f"  [Arama] '{baslik[:60]}' için varsayılan arama yapıldı (simülasyon)")
            sonuc_parts.append("  Durum: Veri bulundu — örnek içerik üretildi")
        elif "yaz" in goal_lower or "write" in goal_lower or "oluştur" in goal_lower:
            sonuc_parts.append(f"  [Yazma] '{baslik[:60]}' için içerik oluşturuldu (simülasyon)")
            sonuc_parts.append("  Durum: İçerik hazır")
        elif "test" in goal_lower or "kontrol" in goal_lower or "check" in goal_lower:
            sonuc_parts.append(f"  [Kontrol] '{baslik[:60]}' için test çalıştırıldı (simülasyon)")
            sonuc_parts.append("  Durum: Test başarılı")
        elif "düzelt" in goal_lower or "fix" in goal_lower or "düzenle" in goal_lower:
            sonuc_parts.append(f"  [Düzeltme] '{baslik[:60]}' için düzenleme yapıldı (simülasyon)")
            sonuc_parts.append("  Durum: Düzeltme uygulandı")
        elif "analiz" in goal_lower or "analyze" in goal_lower or "rapor" in goal_lower:
            sonuc_parts.append(f"  [Analiz] '{baslik[:60]}' analiz edildi (simülasyon)")
            sonuc_parts.append("  Durum: Analiz tamamlandı — 3 bulgu tespit edildi")
        else:
            sonuc_parts.append(f"  [Genel] '{baslik[:60]}' işlendi (simülasyon)")
            sonuc_parts.append("  Durum: Varsayılan işlem tamam")

        return {
            "status": "success",
            "result": "\n".join(sonuc_parts),
            "goal": goal,
            "context": context,
        }

    except Exception as e:
        return {
            "status": "error",
            "result": f"Hata: {type(e).__name__}: {e}\n{traceback.format_exc()}",
            "goal": goal,
            "context": context,
        }


def main():
    """Stdin'den JSON oku, işle, stdout'a JSON yaz."""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            # Hiç girdi yoksa hata döndür
            print(json.dumps({"status": "error", "result": "Stdin boş — JSON girişi bekleniyordu"}))
            sys.exit(1)

        girdi = json.loads(raw)
        goal = girdi.get("goal", "")
        context = girdi.get("context", "")

        sonuc = run(goal, context)
        print(json.dumps(sonuc, ensure_ascii=False))

    except json.JSONDecodeError as e:
        print(json.dumps({
            "status": "error",
            "result": f"JSON ayrıştırma hatası: {e}",
        }))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "result": f"Beklenmeyen hata: {type(e).__name__}: {e}",
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
