---
name: mcp-apps-spec
description: Produce the full MCP Apps contract for a tool that needs an interactive UI resource.
title: "MCP Apps Spec"
version: 1.0.0
phase: 13
lesson: 14
tags: [mcp, apps, ui-resources, csp, iframe-sandbox]
category: mcp-apps-spec
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Produce the full MCP Apps contract for a tool that needs an interactive UI resource. |
| **Nerede** | `misc\mcp-integration\mcp-apps-spec.md` |
| **Ne Zaman** | Genel AI/ML gorevlerinde |
| **Neden** | Mcp Apps Spec islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Produce the full MCP Apps contract for a tool that needs an interactive UI resource. |
| **Nerede?** | mcp-integration/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: AI gelistiricisi
Ne: Produce the full MCP Apps contract for a tool that needs an interactive UI resource.
Nerede: `misc\mcp-integration\mcp-apps-spec.md`
Ne Zaman: Genel AI/ML gorevlerinde
Neden: Mcp Apps Spec islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a tool that would benefit from an interactive UI (timeline, form, dashboard, map, chart), produce the MCP Apps contract.

Produce:

1. `ui://` URI. One canonical name for the UI resource (e.g. `ui://notes/timeline`).
2. Tool result shape. `content[]` with `text` preamble and `ui_resource` block; `_meta.ui` populated.
3. CSP. Minimum allowlist for `default-src`, `script-src`, `connect-src`, `img-src`, `style-src`. Avoid `'unsafe-inline'` unless necessary.
4. Permissions list. Camera / mic / geolocation / network if needed; empty if not.
5. postMessage entry points. Which `host.*` calls the UI will make and what they return.
6. Security checklist. Distinguish-from-host, no clickjacking, strict connect-src, HTML sanitization if any user content is rendered.

Hard rejects:
- CSP with `default-src *`. Wide-open security risk.
- Any `permissions` request beyond what the UI actually uses. Minimum privilege.
- Any ui:// resource that loads external scripts. Bundle or refuse.
- Any UI that renders user-controlled HTML without sanitization. XSS vector.

Refusal rules:
- If the UI is just a static result, refuse to scaffold an App; return text content.
- If the tool would benefit from native host widgets (progress bars, confirmation dialogs), recommend those instead.
- If the host does not yet support MCP Apps (VS Code stable, Zed, Windsurf as of 2026-04), flag fallback-to-text path.

Output: a one-page contract with the `ui://` URI, tool result JSON, CSP, permissions, postMessage entry points, and a security checklist. End with one sentence on the minimum host that will render this UI.
