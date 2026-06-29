# Skills Dizin Yapisi — Konsolidasyon Rehberi

## Kanonik Dizin
**`reymen/cereyan/skills/`** — Tum skill'lerin ana deposu.
Bu dizin altinda kategorilere ayrilmis skill klasorleri bulunur.
Her skill klasoru bir `SKILL.md` dosyasi icerir.

## Legacy Dizinler (kullanilmiyor)
| Eski Dizin | Durum | Aciklama |
|------------|-------|----------|
| `reymen/cereyan/skills_yeni/` | ✅ Tasi̇ndi → `skills/` | Icerik `skills/` altina merge edildi |
| `reymen/cereyan/.ReYMeN/skills/` | 🔴 Legacy | Test skill'leri icerir, referans verilmez |
| `reymen/hafiza/.ReYMeN/skills/` | 🟡 Hafiza | OnceHafiza modulu tarafindan kullanilir (farkli amac) |

## Kod Referanslari
- `skill_utils.py` (`SKILLS_KLASORLERI`): `reymen/arac/skills/`, `.ReYMeN/skills/`, `.agents/skills/`
- `cron_skill_sync.py` (`SKILLS_DIR`): `reymen/cereyan/skills/`
- `reymen_cli/skills_hub.py` (`SKILLS_KLASOR`): `ROOT/.ReYMeN/skills/`

## Not
Yeni skill eklemek icin `reymen/cereyan/skills/<kategori>/<skill_adi>/SKILL.md`
formatini kullan. Bu dizin tum cron/activation/CLI islemleri icin kanonik kaynaktir.
