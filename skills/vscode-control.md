---
name: vscode-control
title: "VS Code Remote Control"
tags: [general]
audience: user
tags: []
category: vscode-control
---

# VS Code Remote Control

Telegram'dan VS Code'u uzaktan kontrol etmek için kullanılır.

## Kullanım

Kullanıcı Telegram'dan şu tür komutlar gönderebilir:
- "VS Code'a şunu yaz: print('merhaba')"
- "VS Code'da Ctrl+S yap"
- "VS Code'da şu dosyayı aç: C:\Users\marko\proje\app.py"

## Komutlar

### Metin yazmak:
```
terminal(command="C:\\Users\\marko\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe C:\\Users\\marko\\AppData\\Local\\hermes\\skills\\vscode-control\\type_in_vscode.py type <metin>")
```

### Tuş kombinasyonu:
```
terminal(command="C:\\Users\\marko\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe C:\\Users\\marko\\AppData\\Local\\hermes\\skills\\vscode-control\\type_in_vscode.py press ctrl+s")
```

### Dosya açmak:
```
terminal(command="C:\\Users\\marko\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe C:\\Users\\marko\\AppData\\Local\\hermes\\skills\\vscode-control\\type_in_vscode.py open C:\\path\\to\\file.py")
```

## Örnek Akış

Kullanıcı: "VS Code'a 'merhaba dünya' yaz"
→ terminal ile type_in_vscode.py çalıştır
→ VS Code'a focus ver
→ metni klavye ile yaz

Kullanıcı: "kaydet"
→ press ctrl+s

Kullanıcı: "geri al"
→ press ctrl+z
