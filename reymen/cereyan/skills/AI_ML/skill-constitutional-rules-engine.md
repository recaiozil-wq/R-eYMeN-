---
name: skill-constitutional-rules-engine
description: Declarative YAML rules engine for output constraints with severity, explanation, fixer operations, and structured diff
title: "Skill Constitutional Rules Engine"
version: 1.0.0
phase: 19
lesson: 86
tags: [safety, rules, constitutional]
category: skill-constitutional-rules-engine
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ML/Veri bilimci |
| **Ne** | Declarative YAML rules engine for output constraints with severity, explanation, fixer operations, and structured diff |
| **Nerede** | `mlops\skills\skill-constitutional-rules-engine.md` |
| **Ne Zaman** | ML modeli egitimi veya deploy gerektiginde |
| **Neden** | Skill Constitutional Rules Engine islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Declarative YAML rules engine for output constraints with severity, explanation, fixer operations, and structured diff |
| **Nerede?** | skills/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: ML/Veri bilimci
Ne: Declarative YAML rules engine for output constraints with severity, explanation, fixer operations, and structured diff
Nerede: `mlops\skills\skill-constitutional-rules-engine.md`
Ne Zaman: ML modeli egitimi veya deploy gerektiginde
Neden: Skill Constitutional Rules Engine islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Constitutional Rules Engine

A constitution is a YAML file. Each rule has `name`, `severity` (low | medium | high), `applies_when` (predicate), `must` (predicate), `explanation`, and optional `fix`.

## Predicates

Atomic:

- `contains_regex` / `not_contains_regex`
- `starts_with_regex` / `ends_with_regex`
- `max_words` / `min_words`

Compositional:

- `all_of: [...predicates]`
- `any_of: [...predicates]`
- `not_: predicate`

## Fix operations

- `append_if_missing: <suffix>`
- `prepend_if_missing: <prefix>`
- `replace_regex: { pattern: <regex>, replacement: <text> }`

## Engine output

`Engine.evaluate(text) -> EngineReport` returns one `RuleResult` per rule with `status` in `pass`, `violation`, `not_applicable`. `report.violations()` filters to violations and `report.max_severity()` returns the worst severity present.

## Artifact

`outputs/rules_report.json` carries draft, revised, and structured diff per case.
