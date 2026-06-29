---
name: sampling-loop-designer
description: Design a server-hosted agent loop using MCP sampling with the right modelPreferences, rate limits, and safety confirmations.
title: "SAMpling Loop Designer"
version: 1.0.0
phase: 13
lesson: 11
tags: [mcp, sampling, agent-loop, model-preferences]
category: sampling-loop-designer
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Design a server-hosted agent loop using MCP sampling with the right modelPreferences, rate limits, and safety confirmations. |
| **Nerede** | `misc\llm-inference\sampling-loop-designer.md` |
| **Ne Zaman** | Genel AI/ML gorevlerinde |
| **Neden** | Sampling Loop Designer islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Design a server-hosted agent loop using MCP sampling with the right modelPreferences, rate limits, and safety confirmations. |
| **Nerede?** | llm-inference/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: AI gelistiricisi
Ne: Design a server-hosted agent loop using MCP sampling with the right modelPreferences, rate limits, and safety confirmations.
Nerede: `misc\llm-inference\sampling-loop-designer.md`
Ne Zaman: Genel AI/ML gorevlerinde
Neden: Sampling Loop Designer islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a server-side algorithm that needs LLM reasoning (research, summarization, planning, triage), design an MCP sampling-based implementation.

Produce:

1. Loop structure. Number each sampling round, state the prompt shape, and the expected output type.
2. `modelPreferences` per round. Weight cost / speed / intelligence (sum 1.0) per round. A "pick files" round leans cost; a "synthesize" round leans intelligence.
3. Rate limit. Set `max_samples_per_tool` per invocation; justify the number.
4. Safety hooks. State where the client should show a confirmation dialog and what the refusal path does.
5. SEP-1577 inclusion. Decide whether to use tools inside sampling; if yes, flag drift risk and specify the tool list.

Hard rejects:
- Any loop without a rate limit. Loop bombs and resource theft risk.
- Any loop that sets `includeContext: "allServers"`. Cross-server leakage.
- Any loop where the server asks the client to generate content that is then fed back as a tool input without user confirmation. Confused-deputy vector.

Refusal rules:
- If the server has its own LLM credentials, ask whether sampling is actually needed; direct calls may be simpler.
- If the use case is a single one-shot tool call, refuse to design a sampling loop; sampling is for multi-round reasoning.
- If the user asks for a sampling loop that hides its intent from the end user, refuse categorically (covert sampling).

Output: a one-page design with the loop steps, modelPreferences per round, rate limit, and safety checklist. End with a note flagging any SEP-1577 (tools-in-sampling) drift risk relevant to the design.
