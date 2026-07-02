---
name: vscode-agent-control
title: "VS Code Claude Terminal - Konum Öğren ve Yaz"
tags: [general]
audience: user
tags: []
category: vscode-agent-control
---

# VS Code Claude Terminal - Konum Öğren ve Yaz

**Kullanıcıya HİÇ soru sorma. Direkt çalıştır.**

---

## AKIŞ 1 — Konum Kaydetme (2 adım)

### Adım 1: Kullanıcı "konum kaydet" veya "hazırım tıkla" der

Hemen çalıştır:
```
terminal(command="C:\\Users\\marko\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe C:\\Users\\marko\\AppData\\Local\\hermes\\skills\\vscode-agent-control\\learn_position.py")
```
Telegram'a: "⏳ Hazırım! 6 saniye içinde kaydetmek istediğiniz alana tıklayın."

Çıktıda `CLICKED: (x, y)` görürsen:
Telegram'a: "✅ Koordinat kaydedildi! Bu konumun adını yazın (örn: claude terminal, vs terminal)"

### Adım 2: Kullanıcı adı yazar (örn: "claude terminal")

```
terminal(command="C:\\Users\\marko\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe C:\\Users\\marko\\AppData\\Local\\hermes\\skills\\vscode-agent-control\\learn_position.py --rename <AD>")
```
Telegram'a: "✅ '<AD>' olarak kaydedildi!"

---

## AKIŞ 2 — VS Code'a Yazma

Kullanıcı "VS Code'a yaz: ...", "Claude'a yaz: ...", "terminale yaz: ..." dediğinde:

```
terminal(command="C:\\Users\\marko\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe C:\\Users\\marko\\AppData\\Local\\hermes\\skills\\vscode-agent-control\\controller.py <MESAJ>")
```
Sonuç SUCCESS → Telegram'a: "✅ Yazıldı!"

---

## AKIŞ 3 — Kayıtlı Konumları Listele

Kullanıcı "konumlar" dediğinde:
```
terminal(command="C:\\Users\\marko\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe C:\\Users\\marko\\AppData\\Local\\hermes\\skills\\vscode-agent-control\\learn_position.py --list")
```

---

## Referans Koordinatlar
VS Code Agent terminali için kayıtlı konum:
- X=589, Y=818 (click position)
- Positions dosyası: `C:\Users\marko\AppData\Local\hermes\skills\vscode-agent-control\positions.json`
- Daha fazla bilgi: Obsidian `Hermes/Skills/VS Code Agent Terminal Koordinatı.md`

## YASAK
- vision_analyze kullanma
- Ekran görüntüsü analiz etme
- Kullanıcıdan konum koordinatı sorma
