
> **Kategori:** media

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Media_Youtube Content |
| **Nerede?** | media/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: youtube-content
description: "YouTube transcripts to summaries, threads, blogs."
title: "Youtube Content"
platforms: [linux, macos, windows]

audience: user
tags: [audio, media, video]
category: media---

# YouTube Content Tool

## When to use

Use when the user shares a YouTube URL or video link, asks to summarize a video, requests a transcript, or wants to extract and reformat content from any YouTube video. Transforms transcripts into structured content (chapters, summaries, threads, blog posts).

Extract transcripts from YouTube videos and convert them into useful formats.

## Setup

```bash
pip install youtube-transcript-api
```

## Helper Script

`SKILL_DIR` is the directory containing this SKILL.md file. The script accepts any standard YouTube URL format, short links (youtu.be), shorts, embeds, live links, or a raw 11-character video ID.

```bash
# JSON output with metadata
python3 SKILL_DIR/scripts/fetch_transcript.py "https://youtube.com/watch?v=VIDEO_ID"

# Plain text (good for piping into further processing)
python3 SKILL_DIR/scripts/fetch_transcript.py "URL" --text-only

# With timestamps
python3 SKILL_DIR/scripts/fetch_transcript.py "URL" --timestamps

# Specific language with fallback chain
python3 SKILL_DIR/scripts/fetch_transcript.py "URL" --language tr,en
```

## Output Formats

After fetching the transcript, format it based on what the user asks for:

- **Chapters**: Group by topic shifts, output timestamped chapter list
- **Summary**: Concise 5-10 sentence overview of the entire video
- **Chapter summaries**: Chapters with a short paragraph summary for each
- **Thread**: Twitter/X thread format — numbered posts, each under 280 chars
- **Blog post**: Full article with title, sections, and key takeaways
- **Quotes**: Notable quotes with timestamps

### Example — Chapters Output

```
00:00 Introduction — host opens with the problem statement
03:45 Background — prior work and why existing solutions fall short
12:20 Core method — walkthrough of the proposed approach
24:10 Results — benchmark comparisons and key takeaways
31:55 Q&A — audience questions on scalability and next steps
```

## Workflow

1. **Fetch** the transcript using the helper script with `--text-only --timestamps`.
2. **Validate**: confirm the output is non-empty and in the expected language. If empty, retry without `--language` to get any available transcript. If still empty, tell the user the video likely has transcripts disabled.
3. **Chunk if needed**: if the transcript exceeds ~50K characters, split into overlapping chunks (~40K with 2K overlap) and summarize each chunk before merging.
4. **Transform** into the requested output format. If the user did not specify a format, default to a summary.
5. **Verify**: re-read the transformed output to check for coherence, correct timestamps, and completeness before presenting.
6. **Post-analysis — "hayata geçir / uygula" requests**: After delivering the analysis, the user may say "bu uygulamayı hayata geçir" or "uygula".
   - Scan the transcript and video title for a **named project/app** (e.g., repo name, tool name, library).
   - If a specific project is named → proceed to clone, install deps, and run it.
   - If the video is **educational/generic** (shows a workflow, not a specific app) → clarify: "Video eğitim videosu, spesifik bir uygulama adı geçmiyor. Hangi projeyi kurmak istiyorsun?"
   - If the user sends a screenshot from the video and your active model has **no vision support** → say so directly: "Modelim görsel göremiyor. Ekranda hangi repo/uygulama adı görünüyor?"

## Pitfalls

- **Non-vision active model**: If the active provider/model lacks vision (e.g. DeepSeek, some OpenRouter models), you CANNOT see screenshots the user sends. Do NOT attempt vision_analyze — it will fail. Tell the user directly and ask them to type the name.
- **Educational videos masquerading as app demos**: Many Turkish YouTube AI tutorials are meta-educational (e.g. "how to clone and run any GitHub project") rather than demos of one specific app. When the user says "bunu kur", always check the transcript for a named project first.

## Error Handling

- **Transcript disabled**: tell the user; suggest they check if subtitles are available on the video page.
- **Private/unavailable video**: relay the error and ask the user to verify the URL.
- **No matching language**: retry without `--language` to fetch any available transcript, then note the actual language to the user.
- **Dependency missing**: run `pip install youtube-transcript-api` and retry.
