---
name: tool-schema-linter
description: Audit a tool registry against production design rules for names, descriptions, parameters, and shape. Can run in CI on every tool-registry change.
title: "Tool Schema Linter"
version: 1.0.0
phase: 13
lesson: 05
tags: [tool-design, linter, selection-accuracy, naming]
category: tool-schema-linter
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Audit a tool registry against production design rules for names, descriptions, parameters, and shape. Can run in CI on every tool-registry change. |
| **Nerede** | `software-development\tool-schema-linter.md` |
| **Ne Zaman** | Ilgili gorev gerektiginde |
| **Neden** | Tool Schema Linter islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Audit a tool registry against production design rules for names, descriptions, parameters, and shape. Can run in CI on every tool-registry change. |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: Yazilim gelistirici
Ne: Audit a tool registry against production design rules for names, descriptions, parameters, and shape. Can run in CI on every tool-registry change.
Nerede: `software-development\tool-schema-linter.md`
Ne Zaman: Ilgili gorev gerektiginde
Neden: Tool Schema Linter islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a tool registry (JSON or Python list), run a static audit against the design rules from Phase 13 · 05 and produce a fix list with severities.

Produce:

1. Name audit. Check `snake_case`, verb-noun order, tense markers, embedded arguments, namespace prefix consistency.
2. Description audit. Enforce length bounds (40 to 1024 chars), the `Use when X. Do not use for Y.` pattern, forbid common injection patterns (`<SYSTEM>`, `ignore previous instructions`, URL shorteners in-line).
3. Schema audit. Typed properties, `required` list present, `additionalProperties: false` on objects, enums on closed sets, no `type: any`, descriptions on string fields.
4. Shape audit. Flag monolithic `action: string` tools when enum exceeds three values. Suggest atomic split.
5. Consistency audit. Same parameter names across related tools; same ID pattern; same unit conventions.

Hard rejects:
- Any tool name that is not `snake_case`. Breaks provider serialization.
- Any description under 40 chars or missing the "Use when" pattern. Selection accuracy tanks.
- Any description containing indirect-injection patterns. Potential tool-poisoning vector.
- Any untyped property. Hallucination bait.

Refusal rules:
- If a registry has more than 64 tools, warn about Anthropic / Gemini per-request limits and route to Phase 13 · 17 for routing.
- If a tool takes untrusted input, reads sensitive data, AND has a consequential executor, refuse and cite Meta's Rule of Two.
- If asked to approve a tool that wraps a production database without a read-only guard, refuse.

Output: one line per finding formatted as `[severity] path: message`, followed by a summary line and a pass/fail verdict. Severity levels: block (must fix before ship), warn (should fix), nit (style). End with the single rewrite that would reduce selection error fastest.
