---
name: android-apk-repackaging
description: APK repackaging pipeline — tek yön, geri dönüşsüz adımlar. Önbelge → Decompile → Yama (karar ağacı) → Rebuild → zipalign → İmzala → Doğrula+logcat.
title: "Android Apk Repackaging"

audience: contributor
tags: [android, coding, development]
category: software-development---

# Android APK Repackaging Pipeline

## Kural

**Tek yön, geri dönüşsüz.** Her adımda başarı kontrolü var. Bir adım geçemezse DUR — sessiz hata bir sonraki adımda patlamaz.

## Gereksinimler

| Araç | Not |
|------|-----|
| apktool.jar | `C:\Users\marko\re-hermes\apktool.jar` |
| zipalign | `$ANDROID_SDK/build-tools/35.0.0/zipalign.exe` |
| apksigner | `$ANDROID_SDK/build-tools/35.0.0/apksigner.bat` |
| jarsigner | **KULLANMA** — sadece v1 imza üretir, Android 7+ yetersiz |
| Python | repack + compression fix için |

---


> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | APK repackaging pipeline — tek yön, geri dönüşsüz adımlar. Önbelge → Decompile → Yama (karar ağacı) → Rebuild → zipalign → İmzala → Doğrula+logcat. |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

## Pipeline

### Adım 0 — ÖNBELGE

APK'yı analiz et:

```bash
java -jar apktool.jar d -f -o _preview/ target.apk
```

Kontrol et:
- **targetSdkVersion:** `grep targetSdk _preview/apktool.yml`
- **minSdkVersion:** `grep minSdk _preview/apktool.yml`
- **Split APK:** `grep -c "isSplitRequired\|requiredSplitTypes\|splitTypes" _preview/AndroidManifest.xml`
- **Native lib:** `find _preview/lib -name "*.so" | wc -l`
- **Obfuscation:** `ls _preview/smali/*/a.smali 2>/dev/null && echo "R8/PROGUARD_VAR"`

```bash
rm -rf _preview/
```

**GATE 0:** Rapor hazırla. Split APK varsa merge planı not et. targetSdk yüksekse düşür. Native lib varsa ZIP_STORED kuralını hatırla.

---

### Adım 1 — DECOMPILE

```bash
cp target.apk target.original.apk
java -jar apktool.jar d -f -o _work/ target.apk

# Resource'suz decompile (opsiyonel — binary manifest korunur)
# java -jar apktool.jar d -r -f -o _work/ target.apk
```

**GATE 1:**
```bash
test -f _work/AndroidManifest.xml && echo "OK" || (echo "DECOMPILE_FAILED"; exit 1)
test -d _work/smali && echo "SMALI_OK" || echo "SMALI_UYARI"
```

---

### Adım 2 — YAMA (Karar Ağacı)

```
Ne değişecek?
├── Manifest → ALT-YORDUM: manifest-patch
├── Resource → ALT-YORDUM: resource-patch
├── Smali/davranış → ALT-YORDUM: smali-patch
└── Split APK merge → ALT-YORDUM: split-merge
```

#### manifest-patch

Dosya: `_work/AndroidManifest.xml` ve `_work/apktool.yml`

```yaml
# apktool.yml — targetSdk düşür
sdkInfo:
  targetSdkVersion: 35
```

```xml
<!-- manifest — debuggable -->
<application android:debuggable="true" ...

<!-- split referanslarını temizle — <manifest> tag'ından: -->
android:isSplitRequired
android:requiredSplitTypes
android:splitTypes

<!-- meta-data'dan sil: -->
splits.required
com.android.vending.splits
stamp.source
stamp.type
```

**GATE 2M:** Değişiklikler dosyada var mı? `grep` ile teyit.

#### resource-patch

- Logo: `_work/res/mipmap-*/` veya `drawable/`
- Renk: `_work/res/values/colors.xml`
- String: `_work/res/values/strings.xml`
- Resource ID: `grep "icon\|logo" _work/res/values/public.xml`

**GATE 2R:** Eski resource kalktı mı? Yeni resource `public.xml`'de referansı var mı?

#### smali-patch

Obfuscated APK'de: mevcut smali'yi anlamaya çalışma — yeni sınıf ekle.

Yeni .smali dosyasını `_work/smali/com/package/` altına yaz. onCreate enjeksiyonu için `.method public final onCreate()V` ara, invoke-super'dan sonra ekle.

**.locals kontrolü:** Kullandığın en yüksek register + 1 <= `.locals X`. Yoksa X'i artır.

**GATE 2S:** `find _work/smali -newer _work/apktool.yml | grep "\.smali$"` ile yeni dosya var mı?

#### split-merge

APKM bundle: base.apk + split_config.<arch>.apk. Tek APK yapmak için:

1. Her iki APK'yı da extract et
2. `split_config.arm64_v8a/lib/arm64-v8a/*.so` → `base/lib/arm64-v8a/`
3. Manifest'ten split referanslarını temizle
4. stamp-cert-sha256 meta-data'sını sil
5. Python ile ZIP_STORED + DEFLATE karışık paketle:

```python
import zipfile, os
out = "base_merged.apk"
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk("base_extracted"):
        for f in sorted(files):
            path = os.path.join(root, f)
            arcname = os.path.relpath(path, "base_extracted")
            if f.endswith(('.so', '.dex', '.png')):
                zf.write(path, arcname, compress_type=zipfile.ZIP_STORED)
            else:
                zf.write(path, arcname, compress_type=zipfile.ZIP_DEFLATED)
```

**GATE 2M (merge):** `python -c "import zipfile; z=zipfile.ZipFile('base_merged.apk'); [print(i.filename, i.compress_type) for i in z.infolist() if i.filename.endswith('.so')]"` ile .so'ların compress_type=0 (STORED) olduğunu doğrula.

---

### Adım 3 — REBUILD

```bash
java -jar apktool.jar b -o _build_unsigned.apk _work/
```

**GATE 3:**
```bash
test -f _build_unsigned.apk && \
  echo "BOYUT: $(stat -c%s _build_unsigned.apk) bytes" || \
  (echo "REBUILD_FAILED"; exit 1)
```

apktool hataları:
- `brut.androlib.AndrolibException` → XML/resource corruption
- `Resource ID not found` → public.xml kaynak listesi bozuk

Hata varsa DUR. 3 başarısız denemeden sonra binary-level patch stratejisine geç.

---

### Adım 4 — ZIPALIGN (Atlanamaz)

```bash
zipalign -p 4 _build_unsigned.apk _build_aligned.apk
```

**GATE 4:**
```bash
zipalign -c 4 _build_aligned.apk | grep -q "Verification successful"
```

Başarısız → APK bozuk. `-f` ile dene.

---

### Adım 5 — İMZALA

**jarsigner KULLANMA.** apksigner zorunlu.

```bash
apksigner sign \
  --ks /c/Users/marko/Desktop/LiveTranscriber/release.keystore \
  --ks-key-alias livetranscriber \
  --ks-pass pass:SIFRE \
  _build_aligned.apk
```

**GATE 5:**
```bash
apksigner verify --verbose _build_aligned.apk | grep -q "v2\|v3"
```

Sadece v1 varsa → jarsigner kullanılmış. Yeniden imzala.

---

### Adım 6 — DOĞRULA (En Değerli Adım)

```bash
adb install _build_aligned.apk

# Install doğrulama
adb shell pm list packages | grep com.package.name

# Logcat
adb logcat -c
adb shell monkey -p com.package.name 1
sleep 3

# Crash kontrolü
adb logcat -d | grep -i "FATAL\|ANR\|Exception\|deadObject" | grep "com.package.name"
```

**GATE 6:**
```bash
CRASHES=$(adb logcat -d | grep -c -i "FATAL\|ANR.*com.package.name")
[ "$CRASHES" = "0" ] && echo "GECTI" || echo "KALDI: $CRASHES crash"
```

Crush varsa logcat'i oku, sebebe göre Adım 2'ye dön.

**Rapor çıktısı:**
```
DURUM: GECTI
targetSdk: 35
Split: merged
Native: 3 .so (STORED ✓)
Obfuscation: R8 var
İmza: v2+v3 ✓
Crash: 0
APK: 14.2 MB
```

---

## Pitfall'lar

1. **"Package invalid / Parse error"** — .so'lar DEFLATE ile sıkıştırılmış. ZIP_STORED ile yeniden paketle.
2. **"App not installed / incompatible"** — Split APK referansları manifest'te kalmış. Temizle.
3. **Signature mismatch** — Farklı keystore. Eski sürümü kaldır veya paket ismi değiştir.
4. **Missing native libs** — Split APK'nın .so'ları base'e merge edilmemiş.
5. **Google Play Services broken** — Orijinal imza gitti, kaçınılmaz.
6. **jarsigner kullanma** — v1-only üretir, Android 16 reddeder.
7. **zipalign sırası kritik** — rebuild → zipalign → apksigner. Sıra bozulursa sessiz hata.
8. **Obfuscated APK** — smali'yi anlamaya çalışma, yeni sınıf ekle.
9. **İmza çakışması** — Aynı uygulamanın iki farklı imzalı sürümü yan yana durmaz.

---

## Skill Dosyaları

| Dosya | Açıklama |
|-------|----------|
| `scripts/patch.sh` (modding skill'inde) | 7 adımlı pipeline scripti — modding skill'i ile ortak kullanılır |
| `references/apk-signature-schemes-android-16.md` | Android 16 imza şemaları detayı |

**patch.sh ortak kullanım:**
```bash
# Modding skill'indeki script'i çağır
bash /c/Users/marko/AppData/Local/hermes/skills/android/android-apk-modding/scripts/patch.sh target.apk full
```
