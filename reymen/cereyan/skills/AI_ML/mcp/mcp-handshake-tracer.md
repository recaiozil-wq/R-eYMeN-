---
name: mcp-handshake-tracer
description: Given a pcap-style transcript of an MCP client-server conversation, annotate every message with its primitive, lifecycle phase, and capability dependency.
title: "MCP Handshake Tracer"
version: 1.0.0
phase: 13
lesson: 06
tags: [mcp, json-rpc, lifecycle, capabilities]
category: mcp-handshake-tracer
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Given a pcap-style transcript of an MCP client-server conversation, annotate every message with its primitive, lifecycle phase, and capability dependency. |
| **Nerede** | `misc\mcp-integration\mcp-handshake-tracer.md` |
| **Ne Zaman** | Genel AI/ML gorevlerinde |
| **Neden** | Mcp Handshake Tracer islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Given a pcap-style transcript of an MCP client-server conversation, annotate every message with its primitive, lifecycle phase, and capability dependency. |
| **Nerede?** | mcp-integration/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: AI gelistiricisi
Ne: Given a pcap-style transcript of an MCP client-server conversation, annotate every message with its primitive, lifecycle phase, and capability dependency.
Nerede: `misc\mcp-integration\mcp-handshake-tracer.md`
Ne Zaman: Genel AI/ML gorevlerinde
Neden: Mcp Handshake Tracer islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a sequence of JSON-RPC 2.0 envelopes captured from an MCP session, produce a walk-through that names each message's primitive, lifecycle phase, and underlying capability flag.

Produce:

1. Per-message annotation. For each `{request, response, notification}`, state: direction (client-to-server or server-to-client), primitive (tools / resources / prompts / roots / sampling / elicitation / lifecycle), lifecycle phase, and the capability flag that had to be negotiated for this message to be valid.
2. Capability check. Reconstruct the `initialize` exchange from the transcript and list all negotiated capabilities. Flag any message that would violate an absent capability.
3. Error diagnostics. For every JSON-RPC error, name the code and the most likely cause given the surrounding context.
4. Completeness audit. Flag a transcript that is missing one of: `initialize`, `initialized` notification, at least one `tools/list` or equivalent, graceful shutdown.
5. Spec compliance. Check each request's params against the 2025-11-25 spec's minimum field set. Flag omissions.

Hard rejects:
- Any message that uses a method outside the spec's allowed set without an `x-` prefix.
- Any `sampling/createMessage` message when the client did not declare the `sampling` capability.
- Any invocation before `notifications/initialized` arrived.

Refusal rules:
- If asked to audit a transcript from a non-MCP protocol, refuse and point at the A2A spec (Phase 13 · 19) as the alternative.
- If asked to "fix" the transcript, refuse. This skill annotates; it does not rewrite. Route corrections through the implementing SDK.

Output: one annotated line per message in arrival order: `[phase/primitive/capability] <method or result shape>`. End with a three-line summary naming any capability violations and any missing lifecycle steps.
