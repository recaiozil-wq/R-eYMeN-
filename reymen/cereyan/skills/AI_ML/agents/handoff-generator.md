---
name: handoff-generator
description: Generate end-of-session handoff packets from workbench artifacts, producing both human-readable Markdown and machine-readable JSON keyed to the seven canonical fields.
title: "Handoff Generator"
version: 1.0.0
phase: 14
lesson: 40
tags: [handoff, generator, session-end, packet, next-action]
category: handoff-generator
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Generate end-of-session handoff packets from workbench artifacts, producing both human-readable Markdown and machine-readable JSON keyed to the seven canonical fields. |
| **Nerede** | `misc\agent-systems\handoff-generator.md` |
| **Ne Zaman** | Genel AI/ML gorevlerinde |
| **Neden** | Handoff Generator islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Generate end-of-session handoff packets from workbench artifacts, producing both human-readable Markdown and machine-readable JSON keyed to the seven canonical fields. |
| **Nerede?** | agent-systems/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: AI gelistiricisi
Ne: Generate end-of-session handoff packets from workbench artifacts, producing both human-readable Markdown and machine-readable JSON keyed to the seven canonical fields.
Nerede: `misc\agent-systems\handoff-generator.md`
Ne Zaman: Genel AI/ML gorevlerinde
Neden: Handoff Generator islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a workbench (state, verdict, review, feedback log, diff), produce a session-end handoff generator wired into the agent runtime.

Produce:

1. `tools/generate_handoff.py` exposing `generate_handoff(snapshot) -> (markdown, payload)`.
2. `outputs/handoff/<session_id>/handoff.md` and `handoff.json`.
3. `handoff.schema.json` covering the seven required fields and the feedback tail format.
4. Session-end hook script that runs the generator and refuses to close the session if any field is missing.
5. `docs/handoff.md` listing the seven fields, their sources, and the trimming policy.

Hard rejects:

- A handoff without a `next_action`. Status reports masquerading as handoffs poison the next session.
- A generator that hand-writes the summary. The agent's job is to leave the workbench in a generatable state.
- A markdown packet that diverges from the JSON. JSON is the source; markdown is a render of JSON.
- A feedback tail longer than 30 entries. The full log is in version control; the packet must stay small.

Refusal rules:

- If the verification report is missing, refuse to generate the packet. A handoff without a verdict is a wish.
- If the review report is missing and a human reviewer was expected, refuse and require the review pass first.
- If the diff summary is empty but the session ran longer than 5 minutes, surface the anomaly before generating; suspect a wedged session rather than a real no-op.

Output structure:

```
<repo>/
├── outputs/handoff/<session_id>/
│   ├── handoff.md
│   └── handoff.json
├── tools/generate_handoff.py
├── handoff.schema.json
└── docs/handoff.md
```

End with "what to read next" pointing to:

- Lesson 41 for end-to-end exercise on a real-style sample app.
- Lesson 42 for packaging the generator into the capstone workbench pack.
- Lesson 29 (Production Runtimes) for wiring session-end into queue, event, and cron triggers.
