
> **Kategori:** android

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Android_Android Apk Modding |
| **Nerede?** | android/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: android-apk-modding
description: APK modding pipeline — tek yön, geri dönüşsüz adımlar. Sistem uygulaması bypass (package rename), split APK merge, smali/dex patching, onPause/onStop boşaltma, manifest düzenleme. Önbelge → Decompile → Yama (karar ağacı) → Rebuild → zipalign → İmzala → Doğrula+logcat.
title: "Android Apk Modding"

audience: contributor
tags: [android, development, mobile]
category: android---

# Android Apk Modding

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Kural | `references/kural.md` |
| Kullanıcı Tercihi | `references/kullan-c-tercihi.md` |
| Gereksinimler | `references/gereksinimler.md` |
| Pipeline | `references/pipeline.md` |
| Mevcut durumu kontrol et: | `references/mevcut-durumu-kontrol-et.md` |
| Eğer "foreground" olarak görünüyorsa, "allow" yap: | `references/e-er-foreground-olarak-g-r-n-yorsa-allow-yap.md` |
| "RECORD_AUDIO: allow" (ops override, bu satır önemli) | `references/record_audio-allow-ops-override-bu-sat-r-nemli.md` |
| ÇALIŞMAZ — sadece root ile | `references/ali-maz-sadece-root-ile.md` |
| enabled=0 = etkin, hidden=true = gizli | `references/enabled-0-etkin-hidden-true-gizli.md` |
| 0a — Bilgi çıkar | `references/0a-bilgi-kar.md` |
| 0b — Preview dizinini temizle | `references/0b-preview-dizinini-temizle.md` |
| Çıktı varsa = SİSTEM UYGULAMASI | `references/kt-varsa-si-stem-uygulamasi.md` |
| apktool.yml → renameManifestPackage: com.yeni.paket.adi | `references/apktool-yml-renamemanifestpackage-com-yeni-paket-adi.md` |
| Slaş format (Lcom/eski/paket/Class;) | `references/sla-format-lcom-eski-paket-class.md` |
| Dot format (Class.forName("com.eski.paket.Class")) | `references/dot-format-class-forname-com-eski-paket-class.md` |
| Orijinal APK'yı yedekle | `references/orijinal-apk-y-yedekle.md` |
| Decompile | `references/decompile.md` |
| _work/smali/com/package/KeepAliveService.smali | `references/_work-smali-com-package-keepaliveservice-smali.md` |
| Çıktı "Verification successful" içermeli | `references/kt-verification-successful-i-ermeli.md` |
| Çıktı "Verified using v1, v2, v3 scheme" içermeli | `references/kt-verified-using-v1-v2-v3-scheme-i-ermeli.md` |
| Ardından telefonu YENİDEN BAŞLAT: | `references/ard-ndan-telefonu-yeni-den-ba-lat.md` |
| 3 saniye bekle, sonra crash kontrolü: | `references/3-saniye-bekle-sonra-crash-kontrol.md` |
| Troubleshooting — Sessiz Hataların Kök Sebebi | `references/troubleshooting-sessiz-hatalar-n-k-k-sebebi.md` |
| APK Yüklenemeyince — Runtime Alternatifleri | `references/apk-y-klenemeyince-runtime-alternatifleri.md` |
| Merge APK Rebuild — Resource Compilation Hataları | `references/merge-apk-rebuild-resource-compilation-hatalar.md` |
| Binary-level Package Name Değiştirme (apktool bypass) | `references/binary-level-package-name-de-i-tirme-apktool-bypass.md` |
| sonra yeni zip yarat, imzalı APK'yı bu binary manifest ile replace et | `references/sonra-yeni-zip-yarat-imzal-apk-y-bu-binary-manifest-ile-repl.md` |
| Skill Dosyaları | `references/skill-dosyalar.md` |
| Ortam hazırlık | `references/ortam-haz-rl-k.md` |
| Full pipeline (önbelge → decompile → rebuild → zipalign → imzala → doğrula) | `references/full-pipeline-nbelge-decompile-rebuild-zipalign-imzala-do-ru.md` |
| Manifest yaması: targetSdk düşür + debuggable aç | `references/manifest-yamas-targetsdk-d-r-debuggable-a.md` |
| Manifest: split APK referanslarını temizle | `references/manifest-split-apk-referanslar-n-temizle.md` |
| Resource değişikliği: renk | `references/resource-de-i-ikli-i-renk.md` |
| Smali: yeni service sınıfı ekle | `references/smali-yeni-service-s-n-f-ekle.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
