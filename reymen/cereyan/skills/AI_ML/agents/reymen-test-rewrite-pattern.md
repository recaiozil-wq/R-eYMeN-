
> **Kategori:** references

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Reymen Test Rewrite Pattern |
| **Nerede?** | references/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# ReYMeN Test Rewrite Pattern — Reference Tests

## Ne Zaman

Hermes reference test'leri (`tests/ReYMeN_reference/`) import hatasi veriyor veya olmayan API'lere bagimli.

## Akis

1. **Hatasi oku** — `ModuleNotFoundError` veya `ImportError`
2. **Ekle veya alias yap** — Eksik import'u kaynak modüle ekle
3. **Namespace cakismasini coz** — Test `.../acp/test_X.py` seklindeyse ve projede de `acp/` paketi varsa:
   - `tests/.../acp/__init__.py`'yi SIL (namespace cakismasi yaratir)
   - Yan etki: pytest direkt directory scan ile test bulamaz. File path vererek calistir.
4. **Test API'sini guncelle** — Test'in cagirdigi API ile mevcut kodun API'si uyusmuyorsa, **test'i mevcut koda gore yeniden yaz**. Eski API'yi taklit etme.
5. **async/await** — `async def` fonksiyon varsa `@pytest.mark.asyncio` + `await` kullan
6. **capsys** — `-p no:capture` ile calisirken `capsys` bulunamazsa, `MagicMock` ile `sys.stdout` patch et

## Ornek: test_server.py (1862 satir → 397 satir, 47 test)

Eski test (Hermes ACP protocol, olmayan API):
```python
from acp.schema import UsageUpdate, UserMessageChunk
from acp_adapter.server import ReYMeNACPAgent
router = build_agent_router(agent, use_unstable_protocol=True)
```

Yeni test (ReYMeN native):
```python
async def test_prompt(self):
    agent = ReYMeNACPAgent()
    result = await agent.prompt("merhaba")
    assert "merhaba" in result["content"]
```

### Test edilen ReYMeN bileşenleri:

| Bileşen | Test Sayısı |
|:--------|:-----------:|
| ACPServer (init, tools, routing, stdio, lifecycle) | 18 |
| ReYMeNACPAgent (init, close, prompt, version) | 6 |
| SessionYoneticisi (CRUD, thread-safety, alias) | 11 |
| acp_adapter/auth exports | 6 |
| acp/schema dataclass'lar | 3 |
| acp/agent/router | 3 |
| **Toplam** | **47** |

## Pitfall — Sonsuz async

`AgentRouter.dispatch` async olduğu için sync lambda kullanma:

```python
# YANLIS:
router.register("test", lambda msg: "handled")
result = router.dispatch("msg")  # coroutine doner, calismaz

# DOGRU:
async def handler(msg):
    return "handled"
router.register("test", handler)
result = await router.dispatch("msg")
```

## Pitfall — no_agent cron script (Windows)

Windows'ta cron ortaminda bash yok. `.sh` script kullanma — `.py` kullan.
