---
name: actor-runtime
description: Build an AutoGen v0.4-shaped actor runtime with private state, inbox-per-actor, message-only IPC, fault isolation, and a dead-letter queue.
title: "Actor Runtime"
version: 1.0.0
phase: 14
lesson: 14
tags: [autogen, actor-model, messaging, fault-isolation, dead-letter]
category: actor-runtime
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Build an AutoGen v0.4-shaped actor runtime with private state, inbox-per-actor, message-only IPC, fault isolation, and a dead-letter queue. |
| **Nerede** | `misc\agent-systems\actor-runtime.md` |
| **Ne Zaman** | Genel AI/ML gorevlerinde |
| **Neden** | Actor Runtime islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Build an AutoGen v0.4-shaped actor runtime with private state, inbox-per-actor, message-only IPC, fault isolation, and a dead-letter queue. |
| **Nerede?** | agent-systems/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: AI gelistiricisi
Ne: Build an AutoGen v0.4-shaped actor runtime with private state, inbox-per-actor, message-only IPC, fault isolation, and a dead-letter queue.
Nerede: `misc\agent-systems\actor-runtime.md`
Ne Zaman: Genel AI/ML gorevlerinde
Neden: Actor Runtime islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a multi-agent task, produce an actor runtime and the agent actors needed.

Produce:

1. A `Message` type with `sender`, `recipient`, `topic`, `body`, `mid`.
2. An `Actor` base class with `receive(message, runtime)`. Actor state is private.
3. A `Runtime` with a shared queue, `send()`, `run_until_idle()`, and a dead-letter queue. Exceptions in handlers go to DLQ; do not propagate.
4. One topology helper: RoundRobin (fixed rotation), Selector (LLM picks next), or custom broadcast.
5. Observability hooks per message: emit OTel spans with `gen_ai.agent.name` and `gen_ai.operation.name` per Lesson 23.

Hard rejects:

- Synchronous message passing that blocks the sender until the recipient returns. That is the v0.2 model; it breaks fault isolation.
- Shared mutable state across actors. Actors read state via messages or not at all.
- A runtime that propagates handler exceptions. Failures belong in the DLQ; let other actors keep running.

Refusal rules:

- If the task has only two actors with a fixed back-and-forth, refuse the actor framing and suggest a prompt chain (Lesson 12). Actors earn cost when there are >=3 actors or async concurrency.
- If the user wants "synchronous mode" for "easier debugging," refuse. Suggest logging + tracing (Lesson 23) instead.
- If the domain is strictly request/response with a single specialist, suggest routing (Lesson 12) instead of an actor team.

Output: `message.py`, `actor.py`, `runtime.py`, `teams.py`, `README.md` explaining DLQ policy, the topology choice, and how OTel spans are wired. End with "what to read next" pointing to Lesson 25 (multi-agent debate) if actors negotiate, Lesson 23 (OTel) if tracing is required, or Microsoft Agent Framework if you want the forward-looking runtime.
