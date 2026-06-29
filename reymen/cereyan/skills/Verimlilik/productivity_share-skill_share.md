
> **Kategori:** productivity

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Productivity_Share Skill_Share |
| **Nerede?** | productivity/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: share
description: Generate a shareable read-only markdown export of the current session, or a short summary. Triggered when the user types /share, /export, 'share session', 'export conversation', or 'save this session'. Use also when the user says 'share' with --summary flag for a condensed recap.
title: "Share"

audience: user
tags: [productivity, tools]
category: productivity---

# /share — Session Export & Summary

When the user triggers this command (by typing `/share`, `/export`, "share this session", "export conversation", etc.), handle it as follows.

## Detect Mode

Check the user's message for `--summary`:
- `--summary` present → summary mode (short recap)
- No `--summary` → full export mode

## Get Session Info

1. Read `$HERMES_SESSION_ID` from the environment:
   ```
   terminal(command="echo $HERMES_SESSION_ID")
   ```
2. Create the exports directory:
   ```
   terminal(command="mkdir -p ~/.hermes/exports/")
   ```

## Full Export Mode

### Step 1 — Retrieve session data

Use session_search in READ mode:

```
session_search(session_id="<session_id>")
```

This returns session_meta (when, source, model) and an array of messages with id, role, content, and timestamp fields.

**Truncation note:** For sessions with more than ~30 messages, `session_search` returns "first 20 + last 10". The gap is lost. If the session is long and the user needs everything, use scroll mode to paginate:

```
session_search(session_id="<id>", around_message_id=<midpoint_id>, window=20)
```

### Step 2 — Build the export

Use `execute_code` to format. Process every message by role:

| Role | Label | Handling |
|------|-------|----------|
| `user` | `User` | Include content as-is |
| `assistant` | `Agent` | Include content. If content is empty but `tool_calls` exists, show function names: `(tool calls: func_name, ...)` |
| `tool` | `Tool ({tool_name})` | Include content, truncated to 2000 chars if longer |
| `session_meta` | — | **Skip entirely** (not a real message) |

### Step 3 — Working Python template

```python
from hermes_tools import write_file
from datetime import datetime
import os

# Hardcode these from the session_search result you saw in your context
session_id = "<from env>"
when = "<from session_meta.when>"
source = "<from session_meta.source>"
model = "<from session_meta.model>"
messages = [
    # paste the messages array from session_search output here
]

lines = []
lines.append(f"# Session Export: {session_id}")
lines.append("")
lines.append(f"**Date:** {when}")
lines.append(f"**Source:** {source}")
lines.append(f"**Model:** {model}")
lines.append(f"**Messages:** {len(messages)}")
lines.append("")
lines.append("---")
lines.append("")

for msg in messages:
    role = msg.get("role", "unknown")

    # Skip session_meta bookmarks
    if role == "session_meta":
        continue

    ts = datetime.fromtimestamp(msg["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")

    if role == "user":
        label = "User"
        content = msg.get("content", "")
    elif role == "assistant":
        label = "Agent"
        content = msg.get("content", "")
        if not content and msg.get("tool_calls"):
            names = [tc["function"]["name"] for tc in msg["tool_calls"]]
            content = f"(tool calls: {', '.join(names)})"
        if not content:
            content = "(no content)"
    elif role == "tool":
        tool_name = msg.get("tool_name", "unknown")
        label = f"Tool ({tool_name})"
        content = msg.get("content", "")
        if len(content) > 2000:
            content = content[:2000] + f"\n\n[... truncated {len(content) - 2000} more chars ...]"
    else:
        label = role.capitalize()
        content = msg.get("content", "")

    if not content.strip() and not msg.get("tool_calls"):
        continue

    lines.append(f"## [{ts}] {label}")
    lines.append("")
    lines.append(content)
    lines.append("")
    lines.append("---")
    lines.append("")

date_str = datetime.now().strftime("%Y-%m-%d")
filename = f"{session_id}-{date_str}.md"
filepath = os.path.expanduser(f"~/.hermes/exports/{filename}")

write_file(path=filepath, content="\n".join(lines))
print(filepath)
```

### Step 4 — Save and confirm

The file is written to:
```
~/.hermes/exports/{session_id}-{today}.md
```

## Summary Mode (--summary)

### Step 1 — Retrieve session data

Same as full export: `session_search(session_id="<session_id>")`

### Step 2 — Synthesize a summary

Review all user and agent messages. Skip tool output — use it for context but don't include it in the summary text.

Write 3-5 sentences covering:
- What the user wanted / the main goal of the session
- What was built, fixed, decided, or investigated
- Key outcomes or deliverables produced
- Any outputs that matter (files created, URLs deployed, decisions made)

If the session is very short (1-2 messages), a 1-2 sentence summary is fine.

### Step 3 — Save

```python
from hermes_tools import write_file
from datetime import datetime
import os

session_id = "<from env>"
when = "<from session_meta.when>"
source = "<from session_meta.source>"
summary = "Your 3-5 sentence summary here..."

lines = [
    f"# Session Summary: {session_id}",
    "",
    f"**Date:** {when}",
    f"**Source:** {source}",
    "",
    "---",
    "",
    summary,
]

date_str = datetime.now().strftime("%Y-%m-%d")
filename = f"{session_id}-{date_str}-summary.md"
filepath = os.path.expanduser(f"~/.hermes/exports/{filename}")

write_file(path=filepath, content="\n".join(lines))
print(filepath)
```

## Delivery

Always print the saved file path:

```
Saved: /home/openclaw/.hermes/exports/{filename}
```

If the session has no messages (count is 0 or session not found in DB):

```
No messages found for session {session_id}. The session may not have been persisted yet — try again after a few messages.
```

## Edge Cases

- **Empty session** — report gracefully (see message above)
- **Long session (>30 messages)** — `session_search` truncates to first 20 + last 10. Note this in a warning at the top of the export. For full export, use scroll pagination.
- **Tool output is huge** — truncate at 2000 characters, mark the truncation
- **`session_meta` role messages** — skip them, they're session bookmarks not real messages
- **Assistant messages with no text, only `tool_calls`** — list the function names
- **`--summary` on a very short session** — 1-2 sentence summary is acceptable
