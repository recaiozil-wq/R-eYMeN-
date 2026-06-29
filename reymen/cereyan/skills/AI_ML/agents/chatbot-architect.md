---
name: chatbot-architect
description: Design a chatbot stack for a given use case.
title: "Chatbot Architect"
version: 1.0.0
phase: 5
lesson: 17
tags: [nlp, agents, chatbot]
category: chatbot-architect
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Design a chatbot stack for a given use case. |
| **Nerede** | `misc\agent-systems\chatbot-architect.md` |
| **Ne Zaman** | Genel AI/ML gorevlerinde |
| **Neden** | Chatbot Architect islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Design a chatbot stack for a given use case. |
| **Nerede?** | agent-systems/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: AI gelistiricisi
Ne: Design a chatbot stack for a given use case.
Nerede: `misc\agent-systems\chatbot-architect.md`
Ne Zaman: Genel AI/ML gorevlerinde
Neden: Chatbot Architect islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a product context (user need, compliance constraints, available tools, data volume), output:

1. Architecture. Rule-based, retrieval, neural, LLM agent, or hybrid (specify which paths go where).
2. LLM choice if applicable. Name the model family (Claude, GPT-4, Llama-3.1, Mixtral). Match to tool-use quality and cost.
3. Grounding strategy. RAG sources, retrieval method (lesson 14), tool contracts.
4. Evaluation plan. Task success rate, tool-call correctness, off-task rate, hallucination rate on held-out dialogs.

Refuse to recommend a pure-LLM agent for any destructive action (payments, account deletion, data modification) without a structured confirmation flow. Refuse to skip the prompt-injection audit if the agent has write access to anything.
