
> **Kategori:** gaming

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Gaming_Pygame Event Driven Cheat |
| **Nerede?** | gaming/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: pygame-event-driven-cheat
description: Pygame oyunlarda event-driven hile/cheat girişi, cooldown, gizli hedef radar, uçma/hızlı koşma efektleri için kalıcı pattern. Windows'ta pygame input polling (get_pressed) yerine KEYDOWN olaylarını dinle, hileyi 120 ms cooldown ile tetikle.
title: "Pygame Event Driven Cheat"

audience: user
tags: [gaming]
category: gaming---

# Pygame Event-Driven Cheat Loop

## Trigger
Pygame oyununda tuş tetiklemeli hile sistemi; Windows'ta çalışırken güvenilir input için event-driven yol şart.

## Core Rules
- `KEYDOWN` üzerinden harf tuşlarına basıldığında `apply_cheat(key)` çağır.
- Her hile tetiklemesinden sonra `last_cheat_time` güncelle; `now - last_cheat_time > 120` ms kontrolü koy.
- Hızlı koşma, uçma, zaman yavaşlatma gibi efektleri `*_timer` değişkenleriyle yönet; her karede 1 azalt.
- Hareket için `get_pressed()` kullan (sürekli basılı yön tuşları için); hile tetikleme için `KEYDOWN` kullan.
- Event döngüsü çok akışı olmayan basit oyunlarda `pygame.event.get()` + işle + çizim şeklinde döner; ekstra event kuyruğu yönetimi yoksa bu yeterli.

## Input Mapping Template
```python
cheat_map = {
    pygame.K_h: ("CAN FULL", lambda: set_lives(3)),
    pygame.K_j: ("HIZ x2 (5 sn)", lambda: set_speed_boost(300)),
    pygame.K_k: ("SKOR +20", lambda: add_score(20)),
    pygame.K_l: ("SIFA MOD (5 sn)", lambda: set_invincible(300)),
    pygame.K_u: ("ZAMAN YAVASLA (3 sn)", lambda: set_slow(180)),
    pygame.K_m: ("MAGNET (4 sn)", lambda: set_magnet(240)),
    pygame.K_f: ("DUSMANLARI DONDUR (4 sn)", lambda: set_freeze(240)),
    pygame.K_p: ("PATLAMA!", lambda: explode_score()),
    pygame.K_r: ("RADAR", lambda: toggle_radar()),
    pygame.K_y: ("UÇMA MODU (10 sn)", lambda: set_fly(600)),
    pygame.K_z: ("SPRINT x4 (5 sn)", lambda: set_sprint(300)),
}
```

## Effect Stacking
- Speed = base * (2 if speed_boost > 0 else 1) * (2 if sprint_timer > 0 else 1)
- Slow = game_speed = 0.5 when slow_timer > 0 else 1.0
- Magnet: 150 px içindeki hedefleri oyuncuya doğru çek.
- Freeze: düşmanlar `move_enemy_randomly` çağrısını atla.
- Global counter: `hile_sayisi`.
- Running effects printed: "AKTİF HİLELER: ...".

## Radars & Hidden Targets
- `radar_active` bool; True ise sağ altta mini harita çiz.
- Gizli hedefler `hidden_targets` listesinde; radar AÇIK olunca ekranda yarı saydam ve büyük çizilir, kapalı olunca 2 px gri nokta halinde.
- Radar çiziminde oyuncu merkez; hedefler/düşmanlar relative offset mini dairede.

## Cooldown
```python
CHEAT_COOLDOWN_MS = 120
last_cheat_time = 0
# event içinde:
if event.key in cheat_map and now - last_cheat_time > CHEAT_COOLDOWN_MS:
    msg = apply_cheat(event.key)
    last_cheat_time = now
```

## Windows Odak Kaybı
- Pygame penceresi arka planda kalırsa `get_pressed()` yanlış okuyabilir; `KEYDOWN` daha dayanıklıdır.
- Penceresi arka plana atma/win+down gibi sistem odak komutlarından kaçın; oyunu tam ekran veya ön planda çalıştır.

## Pitfalls
- `time.sleep()` event döngüsünde girmek; pencere donar. Eğer debounce gerekirse cooldown ms ile yönet, `sleep` kullanma.
- `apply_cheat` içinde `global` kullanımı gerekiyorsa fonksiyon girişinde `global lives, score, speed_boost, invincible, slow_timer, magnet_timer, enemy_freeze, transform_timer, fly_timer, sprint_timer, radar_active` tanımla.
- Uçma modunda yerçekimi ve hız sınırını unutma; `fly_vy` clamp et.
- Düşman hareketinde `dir` özelliği yoksa hata; ilk yüklemede her düşmana rastgele `dir` ata.
- Düşman listesini `pygame.Rect` listesi olarak kurarsan sonradan `dir` ekleyemezsin. Binden itibaren **dict listesi** kullan:
  `{"rect": pygame.Rect(x, y, w, h), "dir": (dx, dy)}`
  Hareket güncellemesi ve çarpışma kontrollerinde her zaman `enemy["rect"]` ve `enemy["dir"]` olarak eriş.

## References
- `references/event-driven-input.md`
- `references/effect-stacking.md`
- `references/hidden-target-radar.md`
