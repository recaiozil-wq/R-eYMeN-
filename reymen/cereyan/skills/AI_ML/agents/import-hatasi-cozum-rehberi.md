
> **Kategori:** references

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Import Hatasi Cozum Rehberi |
| **Nerede?** | references/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Import Hatası Çözüm Rehberi

Test'lerde `ImportError` / `ModuleNotFoundError` ile karşılaştığında uygulanacak sıralı yaklaşım.

## Kural 1 — Önce Module'e Ekle (Test'i Değiştirme)

Test, bir modülden import edemediği bir sembolü çağırıyorsa:

**ÖNCE:** Kaynak modüle eksik sembolü EKLE
**SONRA:** Test çalışıyorsa bitir
**EN SON:** Test hala hatalıysa test'i düzelt

**Neden?** Hermes reference test'leri genellikle eski API'yi yansıtır. Module export eklemek:
- Test'in beklentisini karşılar
- Diğer test'lerde de aynı symbol çalışır
- Geriye uyumluluğu korur

**Örnek — alias ekle:**
```python
# acp_adapter/session.py
SessionManager = SessionYoneticisi  # Test SessionManager import ediyor
```

**Örnek — constant ekle:**
```python
# acp_adapter/server.py
ReYMeN_VERSION = SERVER_INFO["version"]  # Test ReYMeN_VERSION import ediyor
```

**Örnek — class ekle:**
```python
# acp/schema.py (eksik dataclass)
@dataclass
class UsageUpdate:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
```

## Kural 2 — Namespace Çakışması

Test dizini (`tests/xxx/acp/`) proje paketi (`acp/`) ile aynı ada sahipse:

**Semptom:** `ModuleNotFoundError: No module named 'acp.agent'` 
ama `python3 -c "from acp.agent.router import ..."` çalışıyor.

**Çözüm:** Test dizinindeki `__init__.py`'yi SİL:
```bash
rm tests/ReYMeN_reference/acp/__init__.py
```
Artık pytest projenin `acp/` paketini görebilir.

**Alternatif:** Eğer testlerin ayrı paket olarak kalması gerekiyorsa,
test dosyasında sys.path manipülasyonu yap veya conftest.py'ye path
ekle. Ama `__init__.py` silmek en temiz çözüm.

## Kural 3 — Soğan Katmanı Yaklaşımı

Import hatalarını tek tek çöz:

1. `pytest test_xxx.py -x` çalıştır — ilk hatada dur
2. Hatayı oku — hangi modül/sembol eksik?
3. Kural 1 veya 2 uygula
4. Tekrar çalıştır — bir sonraki hata çıkar
5. Tüm import hataları bitene kadar tekrarla

Her adımda SADECE bir hatayı çöz. Toplu tahmin yapma — her çözüm
bir sonraki katmanı açar.

## Gerçek Hayat Örneği (2026-06-21)

| Sıra | Hata | Çözüm |
|:----:|:-----|:------|
| 1 | `TERMINAL_SETUP_AUTH_METHOD_ID` auth'da yok | auth.py'ye eklendi |
| 2 | `No module named 'acp.agent'` | `__init__.py` silindi |
| 3 | `UsageUpdate` schema'da yok | schema.py'ye eklendi |
| 4 | `UserMessageChunk` schema'da yok | schema.py'ye eklendi |
| 5 | `ReYMeN_VERSION` server'da yok | server.py'ye alias eklendi |
| 6 | `SessionManager` session'da yok | session.py'ye alias eklendi |
