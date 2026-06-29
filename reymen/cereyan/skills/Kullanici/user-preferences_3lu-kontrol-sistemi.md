---
name: 3lu-kontrol-sistemi
id: 3lu-kontrol-sistemi
title: "Üçlü Kontrol Sistemi — v2.0"
description: "Her görev sonunda 3 ajanlı kontrol: (1) işlem tamamlandı mı (2) doğru yapıldı mı (3) kayıt doğru girildi mi"
tags: [kontrol, quality-assurance, dogrulama, kayit, always-active]
category: user-preferences
audience: user
trigger: "Her görev tamamlandığında — son adım olarak çalıştır"
---


> **Kategori:** preferences

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Her görev sonunda 3 ajanlı kontrol: (1) işlem tamamlandı mı (2) doğru yapıldı mı (3) kayıt doğru girildi mi |
| **Nerede?** | preferences/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# ÜÇLÜ KONTROL SİSTEMİ — v2.0

**ZORUNLU:** Her görev tamamlandığında bu skill çalıştırılır. Atlanamaz.

---

## ÖN KOŞUL — ANINDA GÜNLÜK KAYDI (KESİN KURAL)

Her işlem adımı yapıldığı ANDA günlük dosyasına yazılır. Bekletme, biriktirme, sonra yazarım yok.

- Günlük yolu: `C:\Users\marko\OneDrive\Desktop\hermes calisma gunlugu\hermes GG.AA.YYYY.txt`
- Dosya yoksa oluştur, varsa ekle
- Kullanıcının söylediği cümle aynen yazılır (düzeltme yapma, olduğu gibi bırak)
- Her işlem: numaralı madde + kullanıcı sözü + yapılan komut/adım + not/varsa hata
- Kullanıcı bunu denetliyor, kontrol ediyor

---

## AKIŞ

Görev bittiğinde, cevabı kullanıcıya göndermeden ÖNCE şu 3 kontrolü yap:

### KONTROL 1 — TAMAMLAMA DENETİMİ
- Görevin tüm adımları eksiksiz yapıldı mı?
- Kullanıcının dediği her şey yerine getirildi mi?
- Eksik adım varsa tamamla, yoksa geç.

### KONTROL 2 — DOĞRULUK DENETİMİ
- Yapılan işlemler doğru mu?
- Hata/eksik/yanlış yönlendirme var mı?
- **Windows dosya kuralı:** Tüm dosyalara `.txt` veya uygun uzantı ekle. Uzantısız dosya Windows'ta simge göstermez, Notepad açmayı bilmez.
- **Git Bash tuzağı:** `taskkill /f` gibi Windows parametreleri Git Bash'te MSYS yol dönüşümüne takılır. `powershell -NoProfile -Command "taskkill /f /im ..."` ile sarmala.
- Önceki hatalardan ders alındı mı? Varsa düzelt.

### KONTROL 3 — KAYIT DENETİMİ
- İşlem adımları çalışma günlüğüne doğru girildi mi?
- Günlük formatı: `C:\Users\marko\OneDrive\Desktop\hermes calisma gunlugu\hermes GG.AA.YYYY.txt`
- Kullanıcının söylediği cümleler aynen kaydedildi mi?
- Anında kayıt kuralına uyuldu mu? (bekletme yapılmadı mı?)
- Eksik kayıt varsa tamamla.

---

## ÇIKTI FORMATI

Görev cevabının EN SONUNA şu etiketi ekle:

---
✓ 3-KONTROL: TAMAMLAMA [OK/FAIL] | DOĞRULUK [OK/FAIL] | KAYIT [OK/FAIL]

---

## YAYGIN HATALAR (PITFALLS)

1. **Uzantısız dosya** — Windows'ta simge göstermez, Notepad açmayı bilmez. Her dosyaya uzantı (.txt, .py, .md) ekle.
2. **Git Bash + Windows komutları** — `/f`, `/im` gibi parametreler MSYS tarafından Unix yolu sanılır. `powershell -NoProfile -Command` wrapper kullan.
3. **Günlük biriktirme** — "Oturum sonunda yazarım" hatası. Her adım anında yazılmalı.
4. **Kullanıcı sözünü düzeltme** — Kullanıcının yazdığı cümle aynen kaydedilir, düzeltilmiş hali değil.
5. **Türkçe karakterli yollar (KRİTİK)** — Git Bash (MSYS) Türkçe 'ı' (noktasız i) karakterini 'i' olarak dönüştürebilir. Kullanıcı "calisma" (i) yazar, ama Windows klasör adı "calısma" (ı) olabilir. İki farklı klasör! Çözüm: execute_code ile Python os.path.exists() kullanarak BOTH varyasyonu kontrol et. write_file doğru karakterle yazar ama read_file aynı karakterle okumazsa YOK der.
6. **OneDrive Files On-Demand tuzağı** — Klasör OneDrive altındaysa, dosya yazıldıktan sonra OneDrive buluta taşıyabilir. `write_file` başarılı olsa bile hemen ardından `read_file` ile doğrulama yap.
