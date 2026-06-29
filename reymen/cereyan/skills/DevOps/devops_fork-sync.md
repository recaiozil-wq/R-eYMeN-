---
name: fork-sync
description: Compare forked agent codebase with upstream (Hermes), identify gaps, sync changes, and fix test failures.
tags: [hermes, reymen, fork, sync, merge, codebase-comparison]
audience: maintainer
---


> **Kategori:** devops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Compare forked agent codebase with upstream (Hermes), identify gaps, sync changes, and fix test failures. |
| **Nerede?** | devops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Fork Sync — Agent Codebase Karşılaştırma ve Güncelleme

Related: [`github-self-update`](devops/github-self-update) — after initial sync, switch to self-update pattern

Bir Hermes Agent fork'unu (ReYMeN vb.) upstream ile karşılaştırır, eksikleri bulur, güvenli dosyaları kopyalar, merge gerektirenleri işaretler.

## Ne Zaman Kullanılır

- Hermes güncellendiğinde fork'a çekmek için
- Fork'un Hermes'ten ne kadar uzaklaştığını ölçmek için
- Hangi dosyaların değiştirildiğini / eklendiğini / silindiğini görmek için

## Adımlar

### 1. Yapısal Karşılaştırma

```bash
# Klasör yapısını karşılaştır
diff <(cd /path/to/hermes && ls -d */ | sort) <(cd /path/to/fork && ls -d */ | sort)

# .py dosya sayısı
find . -name '*.py' -not -path '*/node_modules/*' -not -path '*/venv/*' -not -path '*/__pycache__/*' -type f | wc -l

# Modül bazında dosya sayısı
for d in tools plugins gateway providers; do
  echo "$d: $(find "$d" -name '*.py' -type f 2>/dev/null | wc -l)"
done
```

### 2. Kopyalanabilir Dosyaları Belirle (Değiştirilmemiş)

Fork'ta değiştirilmemiş, direkt kopyalanabilir dosyalar:

```
AGENTS.md, CONTRIBUTING.md, .env.example, .gitignore
Dockerfile, docker-compose.yml
docs/, assets/, packaging/
```

Kopyalama:

```bash
for f in AGENTS.md .env.example CONTRIBUTING.md; do
  cp "$HERMES/$f" "$FORK/$f"
done
for d in docs assets packaging; do
  cp -r "$HERMES/$d" "$FORK/"
done
```

### 3. Merge Gerektiren Dosyaları İşaretle

Fork'ta değiştirilmiş olan dosyalar **elle merge** gerektirir:

```bash
# Fork'ta değiştirilmiş dosyaları bul
for f in motor.py main.py beyin.py sistem_talimati.py; do
  diff -q "$HERMES/$f" "$FORK/$f" >/dev/null 2>&1 || echo "⚠ $f DEĞİŞMİŞ"
done
```

### 4. Fork'a Özel Eklenenleri Tespit Et

```bash
# Fork'ta olup Hermes'te olmayan dosyalar
diff <(cd $HERMES && find . -name '*.py' -not -path '*/node_modules/*' | sort) \
     <(cd $FORK && find . -name '*.py' -not -path '*/skills/*' -not -path '*/tests/hermes_reference/*' | sort) \
     2>/dev/null | grep "^>"
```

### 5. Test Fix'leri (Yaygın Fork Sorunları)

Fork testlerinde sık karşılaşılan hatalar ve çözümleri:

| Hata | Çözüm |
|------|-------|
| `ValueError: I/O operation on closed file` | pytest stdout capture sorunu. `addopts = -s` ekle veya testi hafif import'larla yeniden yaz |
| `Bilinmeyen arac 'XXX'` | ToolRegistry'de kayıtlı değil. Registry'e ekle veya `_fallback_calistir()`'e taşı |
| `'SaglayCiAdim' object is not subscriptable` | Dict yerine object kullanıma geçmiş. `[0]["provider"]` → `[0].provider` |
| `AssertionError: 'eski metin'` | Kod değişmiş, test güncellenmemiş. Gerçek çıktıyı oku, test beklentisini güncelle |
| timeout (test dosyası) | İçinde ağ çağrısı, zip oluşturma veya 5000 trivial test var. Testi yeniden yaz |

### 6. Sync Cron Job'u Ekle

```bash
hermes cron create \
  --name "fork-sync" \
  --schedule "0 3 * * 1" \
  --prompt "Fork'u upstream ile senkronize et."
```

## Pitfall'lar

- **ToolRegistry prefix farkı**: Registry `[Hata]: Bilinmeyen arac` döner, motor `[Bilinmeyen arac]` bekler. Registry'deki prefix'i düzelt.
- **Ölü kod**: Fork'ta `calistir()` içinde `_fallback_calistir()`'dan sonra kalan if blokları hiç çalışmaz. Taşı veya sil.
- **Büyük test dosyaları**: 5000 trivial test (test_bulk_5000.py gibi) pytest'i dondurur. Bunları sil veya küçült.
- **import zinciri**: `from main import ...` tüm sistemi yükler ve pytest capture'ını kırar. Parçalı import yap.
- **__pycache__**: Değişiklik sonrası `rm -rf __pycache__` unutulursa eski bytecode çalışır.
