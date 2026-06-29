---
name: orchestration-picker
description: Pick an orchestration topology (supervisor, swarm, hierarchical, debate, or none) for a given problem and implement it minimally.
title: "Orchestration Picker"
version: 1.0.0
phase: 14
lesson: 28
tags: [orchestration, supervisor, swarm, hierarchical, debate]
category: orchestration-picker
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Pick an orchestration topology (supervisor, swarm, hierarchical, debate, or none) for a given problem and implement it minimally. |
| **Nerede** | `misc\agent-systems\orchestration-picker.md` |
| **Ne Zaman** | Genel AI/ML gorevlerinde |
| **Neden** | Orchestration Picker islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Pick an orchestration topology (supervisor, swarm, hierarchical, debate, or none) for a given problem and implement it minimally. |
| **Nerede?** | agent-systems/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: AI gelistiricisi
Ne: Pick an orchestration topology (supervisor, swarm, hierarchical, debate, or none) for a given problem and implement it minimally.
Nerede: `misc\agent-systems\orchestration-picker.md`
Ne Zaman: Genel AI/ML gorevlerinde
Neden: Orchestration Picker islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a product domain and a task class, pick the minimal topology.

Decision:

1. 1 agent + workflow patterns (Lesson 12) suffice? -> don't use topology at all.
2. 2-4 specialists with distinct responsibilities? -> **supervisor-worker**.
3. Latency-critical and specialists can cleanly hand off? -> **swarm**.
4. 10+ specialists, supervisor context budget failing? -> **hierarchical**.
5. Accuracy matters more than cost, multi-proposer + critique helps? -> **debate** (Lesson 25).

Produce:

1. The chosen topology scaffold.
2. Hop counter on swarm; nesting depth limit on hierarchical; round cap on debate.
3. Observability hooks per handoff or per step (OTel GenAI spans, Lesson 23).
4. A "why this, not that" README section.

Hard rejects:

- Calling 3 LLM calls in sequence "multi-agent." That's a prompt chain.
- Swarm without hop counter. Bouncing is a certainty.
- Hierarchical that bottoms out at 1 specialist per branch. Flatten.

Refusal rules:

- If the user wants multi-agent for a task that a single ReAct loop handles, refuse and suggest Lesson 01.
- If the user wants supervisor for a 2-step task, refuse and suggest prompt chaining (Lesson 12).
- If the domain has compliance / audit requirements, refuse swarm and suggest supervisor or hierarchical.

Output: topology scaffold + README with decision rationale. End with "what to read next" pointing to Lesson 13 (LangGraph) for supervisor implementation, Lesson 16 (OpenAI Agents SDK) for handoffs-as-tools, or Lesson 25 for debate specifics.
