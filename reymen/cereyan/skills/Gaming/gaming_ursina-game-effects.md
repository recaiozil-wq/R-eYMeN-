
> **Kategori:** gaming

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Gaming_Ursina Game Effects |
| **Nerede?** | gaming/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: ursina-game-effects
description: Ursina ile first-person 3D voxel oyununda etkili hile/efekt sistemi, koşullu tetikleme, otomatik efektler ve blok yerleştirme/kırma kalıcı patterni. Pygame yaklaşımından farklı event/debounce ve mouse hover döngüsü kurallarını kapsar.
title: "Ursina Game Effects"

audience: user
tags: [gaming]
category: gaming---

# Ursina First-Person Cheat Effects
## Trigger
Ursina/Minecraft-style first-person 3D voxel oyununda hile/efekt sistemi, blok yerleştirme/kırma ve otonom input döngüsü için kalıcı pattern. Bu skill sadece efektleri değil; 3D yerleşim/kırma, conditional auto-cheat, debounce, variable scope ve görsel doğrulama kurallarını kapsar.

## Trigger
Ursina engine ile yazılmış 3D oyuna Minecraft tarzı komut efekti (güç, hız, uçma, can dolturma) eklenmesi gerektiğinde.

## Core Rules
- Etkileri Ursina `input(key)` içinde `KEYDOWN` benzeri string tuş tetiklemeleriyle aç/kapat.
- Pygame'deki `pygame.event.get()` loop falan yok; Ursina `input()` event hook kullanır.
- Basış tekrarını önlemek için string `last_toggle[key]` + `time.time()` farkıyla debounce uygula, örn: 0.35 sn.
- Oyun başlangıcında her zaman açık kalması gereken efektleri `auto_effects` listesiyle ilkle.
- Can/ortalama gibi koşullu tetiklemeleri `conditional_rules` sözlüğünde `lambda` olarak tanımla ve `update()` içinde her karede değerlendir.
- Mouse hover objesi: `mouse.hovered_entity`. Blok yerleştirmede yeni konum: `hit.position + mouse.normal`.

## Input Mapping Template
```python
effects = {
    'strength': False,
    'resistance': False,
    'regeneration': False,
    'speed': False,
    'creative': False,
}
auto_effects = ['speed']
conditional_rules = {
    'regeneration': lambda: player_health < int(player_max_health * 0.7),
    'resistance': lambda: player_health < int(player_max_health * 0.4),
}
min_interval = 0.35
last_toggle = {'g': 0, 'r': 0, 'e': 0, 's': 0, 'c': 0}

def input(key):
    now = time.time()
    if key in last_toggle and now - last_toggle[key] >= min_interval:
        if key == 'g':
            effects['strength'] = not effects['strength']
            print(f"Strength: {'Açık' if effects['strength'] else 'Kapalı'}")
            last_toggle[key] = now
        if key == 'r':
            effects['resistance'] = not effects['resistance']
            print(f"Resistance: {'Açık' if effects['resistance'] else 'Kapalı'}")
            last_toggle[key] = now
        if key == 'e':
            effects['regeneration'] = not effects['regeneration']
            print(f"Regeneration: {'Açık' if effects['regeneration'] else 'Kapalı'}")
            last_toggle[key] = now
        if key == 's':
            effects['speed'] = not effects['speed']
            print(f"Speed: {'Açık' if effects['speed'] else 'Kapalı'}")
            last_toggle[key] = now
        if key == 'c':
            effects['creative'] = not effects['creative']
            player.gravity = 0 if effects['creative'] else 1
            print(f"Creative: {'Açık' if effects['creative'] else 'Kapalı'}")
            last_toggle[key] = now
```

## Effect Application in update()
```python
def update():
    # koşullu efektler
    for k in conditional_rules:
        if not effects.get(k):
            effects[k] = bool(conditional_rules[k]())

    # hız
    player.speed = 12 if effects['speed'] else 5

    # rejenerasyon
    if effects['regeneration'] and player_health < player_max_health:
        player_health = min(player_max_health, player_health + 0.2)

    # creative uçma
    if effects['creative']:
        if held_keys['space']:
            player.y += 6 * time.dt
        if held_keys['shift']:
            player.y -= 6 * time.dt
```

## Block Interaction Template
```python
if key == 'left mouse down':
    hit = mouse.hovered_entity
    if hit and hit in ground:
        if effects['strength']:
            destroy(hit)
if key == 'right mouse down':
    hit = mouse.hovered_entity
    if hit:
        new_pos = hit.position + mouse.normal
        Button(model='cube', texture=block_to_place, position=new_pos, parent=scene, origin_y=0.5)
```

## Verification Rule
- Ursina/3D proje sonrası test sırasında "çalışıyor" demeden önce ekran görüntüsü al.
- Görselde 3D blok ortamı, ilk kişi bakış açısı, çapraz ve boş/karalanmış alan olmamasını doğrula.
- Boş ekran kabul edilebilir başarı sayılmaz.

## Output Rule
- Kullanıcı sadece yazılı çıktı istedi; sesli bildirim, TTS, voice memo kullanma.
- Konsol `print` ile efekt durumunu yaz; ekran çıktısı yeterli.

## Pitfalls
- `time.time()` debounce'u `time.dt` ile karıştırma; `time.dt` kareden kareye değişir, `time.time()` için sabit kronometre kullan.
- Ursina render testini konsol çıktısıyla (exit code 0) kanıtlamaya çalışma; GUI penceresi için ekran görüntüsü şart.
- `ground` listesini `Button` listesi olarak kur; `mouse.hovered_entity` kimliği karşılaştırması için `in ground` kullan.
- `player_health` mobil/platform farkı olmaması için global ya da controller attribute olarak tanımla; closure içinde hata vermesin.
- `FirstPersonController` varsayılan gravity 1'dir; `creative` açarken `player.gravity = 0` yap.

## References
- `references/ursina-input-hooks.md`
- `references/ursina-block-placement.md`
- `references/ursina-render-verification.md`
