
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Video ajanı |
| **Ne?** | Ecc_Videodb |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: videodb
description: See, Understand, Act on video and audio. See- ingest from local files, URLs, RTSP/live feeds, or live record desktop; return realtime context and playable stream links. Understand- extract frames, build visual/semantic/temporal indexes, and search moments with timestamps and auto-clips. Act- transcode and normalize (codec, fps, resolution, aspect ratio), perform timeline edits (subtitles, text/image overlays, branding, audio overlays, dubbing, translation), generate media assets (image, audio, video), and create real time alerts for events from live streams or desktop capture.
title: "Videodb"
origin: ECC
allowed-tools: Read Grep Glob Bash(python:*)
argument-hint: "[task description]"

audience: contributor
tags: [ai, automation, development, video]
category: ecc---

# Videodb

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| VideoDB Skill | `references/videodb-skill.md` |
| When to use | `references/when-to-use.md` |
| How it works | `references/how-it-works.md` |
| URL | `references/url.md` |
| YouTube | `references/youtube.md` |
| Local file | `references/local-file.md` |
| force=True skips the error if the video is already indexed | `references/force-true-skips-the-error-if-the-video-is-already-indexed.md` |
| Always wrap in try/except and treat "No results found" as empty. | `references/always-wrap-in-try-except-and-treat-no-results-found-as-empt.md` |
| index already exists. Extract the existing index ID from the error. | `references/index-already-exists-extract-the-existing-index-id-from-the-.md` |
| Use score_threshold to filter low-relevance noise (recommended: 0.3+) | `references/use-score_threshold-to-filter-low-relevance-noise-recommende.md` |
| Change resolution, quality, or aspect ratio server-side | `references/change-resolution-quality-or-aspect-ratio-server-side.md` |
| Always prefer reframing a short segment: | `references/always-prefer-reframing-a-short-segment.md` |
| Async reframe for full-length videos (returns None, result via webhook): | `references/async-reframe-for-full-length-videos-returns-none-result-via.md` |
| Presets: "vertical" (9:16), "square" (1:1), "landscape" (16:9) | `references/presets-vertical-9-16-square-1-1-landscape-16-9.md` |
| Custom dimensions | `references/custom-dimensions.md` |
| Error handling | `references/error-handling.md` |
| Examples | `references/examples.md` |
| Additional docs | `references/additional-docs.md` |
| Provenance | `references/provenance.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
