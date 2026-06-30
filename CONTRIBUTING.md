# Katkı Rehberi / Contributing Guide

ReYMeN'e katkıda bulunduğun için teşekkürler! 🎉

## 🚀 Hızlı Başlangıç

```bash
# 1. Fork'la ve clone'la
git clone https://github.com/KULLANICI_ADIN/ReYMeN-Ajan.git
cd ReYMeN-Ajan

# 2. Sanal ortam oluştur
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Geliştirme bağımlılıklarını yükle
pip install -e ".[dev,full]"

# 4. Pre-commit hook'larını kur
pre-commit install

# 5. Test et
pytest tests/ -v
```

## 📝 Katkı Süreci

1. **Issue aç** — Ne yapmak istediğini önce tartışalım
2. **Branch aç** — `feature/` veya `fix/` önekiyle
3. **Kodla** — Mevcut stile uygun yaz
4. **Test ekle** — Yeni kod %70+ coverage
5. **Lint kontrolü** — `ruff check .`
6. **PR aç** — Template'i doldur

## ✅ Kod Standartları

| Kural | Açıklama |
|:------|:---------|
| Türkçe docstring | Tüm fonksiyonlar Türkçe açıklama |
| Ruff uyumu | `ruff check . --fix` ile düzelt |
| Except pass yok | `except: pass` kullanma, en az `logging.warning` |
| Tip ipuçları | Mümkünse type hint ekle |
| Testler | `tests/` dizininde, ilgili modülün testi |

## 🧪 Test

```bash
# Tüm testler
pytest tests/ -v

# Coverage ile
pytest --cov=reymen tests/

# Belirli modül
pytest tests/test_beyin.py -v

# Hızlı (timeout hassas testler atlanır)
pytest tests/ -v --ignore=tests/hermes_legacy
```

## 🐛 Hata Bildirimi

Issue template'ini kullan:
- Hangi ortam (OS, Python versiyonu)
- Hata mesajı/log
- Tekrarlama adımları
- Beklenen davranış

## 💬 İletişim

- Telegram: @Pasa_38
- GitHub Issues: Tercih edilen yöntem
