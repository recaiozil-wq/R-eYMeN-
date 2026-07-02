---
name: ai-video-content-pipeline
description: Automate AI-powered short video creation. Covers MoneyPrinterTurbo setup, Pexels API integration, LLM configuration (DeepSeek/Gemini), TTS voice setup, local video fallback, and failure recovery patterns. NOT for manual video editing workflows (Adobe Premiere, DaVinci Resolve).
title: "AI Video Content Pipeline"

audience: user
tags: [content, creative, video]
category: content-creation---

# AI Video Content Pipeline

Automated short-video generation using AI — script → voice → video clips → final export.

## When to Use

- User wants to create short videos automatically from a topic/keyword
- User mentions MoneyPrinterTurbo or similar AI video tools
- User needs to configure Pexels/Pixabay/Coverr API for stock footage
- User encounters TTS/LLM/video-source failures

## Pipeline Stages

1. **Script Generation** — LLM (DeepSeek, OpenAI, Gemini, etc.) writes a short video script
2. **Search Terms** — LLM generates search keywords for stock footage
3. **TTS / Voiceover** — Text-to-speech generates audio (Edge TTS, Azure, Gemini TTS)
4. **Video Material** — Stock footage downloaded from Pexels/Pixabay or local files
5. **Combining** — Video clips concatenated with ffmpeg
6. **Final Render** — Audio + subtitles + BGM merged into final video

## Setup

### Quick Install (MoneyPrinterTurbo)

```bash
git clone https://github.com/harry0703/MoneyPrinterTurbo.git
cd MoneyPrinterTurbo
uv sync --frozen
```

### Python Venv Alternative

```bash
python3.11 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running

### WebUI (Recommended)

```bash
# Windows — from project root:
.venv/Scripts/python.exe -m streamlit run webui/Main.py --server.port=8501 --server.headless=true
```

Access at `http://localhost:8501`

### Backend API

```bash
.venv/Scripts/python.exe main.py
```

API docs at `http://localhost:8080/docs`

### CLI

```bash
.venv/Scripts/python.exe cli.py --video-subject "Konu" --video-source pexels --voice-name "tr-TR-EmelNeural" --no-subtitle-enabled
```

## Configuration

### config.toml Key Settings

```toml
[app]
llm_provider = "deepseek"          # deepseek, openai, ollama, gemini, etc.
deepseek_api_key = "sk-..."        # from platform.deepseek.com
deepseek_model_name = "deepseek-chat"
video_source = "pexels"            # pexels, pixabay, coverr, local
pexels_api_keys = ["your-key"]     # array!
voice_name = "tr-TR-EmelNeural"    # Edge TTS (free). See docs/voice-list.txt
bgm_type = "random"                # random, local, none
bgm_volume = 0.2
subtitle_provider = "edge"         # edge, whisper
```

### Voice List

Available voices: `docs/voice-list.txt`

Common Turkish: `tr-TR-EmelNeural` (female), `tr-TR-AhmetNeural` (male)

### CLI Flags

| Flag | Description |
|---|---|
| `--video-subject` | Topic/keyword (required) |
| `--video-source` | pexels, pixabay, coverr, local |
| `--video-materials` | Comma-separated local video files |
| `--stop-at` | Pipeline stage: script, terms, audio, subtitle, materials, video |
| `--voice-name` | TTS voice name |
| `--no-subtitle-enabled` | Disable subtitles |
| `--video-aspect` | 9:16 (default) or 16:9 |

## Common Failures & Fixes

### 1. LLM Error: "api_key is not set"

```
Error: deepseek: api_key is not set
```

Check `config.toml` has the correct key. WebUI's `save_config()` may overwrite and blank the key — re-add it after WebUI usage.

### 2. TTS Error: "Invalid voice ''" or "failed to generate audio"

The voice name is empty or invalid. Always pass `--voice-name` in CLI or set it in config.toml.

### 3. Gemini TTS: "API key is not set"

If user selects `gemini:Zephyr-Female` in WebUI but has no Gemini API key, apply this fix:

In `app/services/voice.py`, modify the `is_gemini_voice` branch in `tts()`:

```python
elif is_gemini_voice(voice_name):
    gemini_key = config.app.get("gemini_api_key", "")
    if not gemini_key:
        logger.warning(f"Gemini API key not set, falling back to Edge TTS")
        return azure_tts_v1(text, "tr-TR-EmelNeural", voice_rate, voice_file)
    # ... normal gemini_tts call
```

### 4. Pexels "file does not exist" with local source

Local videos must be in `storage/local_videos/` directory. The security check `resolve_path_within_directory` only allows files under that path. Use absolute paths or relative to project root.

### 5. Port Already in Use

```bash
netstat -ano | grep ":8501"
taskkill /F /PID <PID>
```

### 6. No ffmpeg

MoviePy auto-downloads ffmpeg, but if it fails set `ffmpeg_path` in config.toml or install manually.

## Custom Video Generation (MoviePy)

When MoneyPrinterTurbo cannot match the desired scene sequence, write a custom Python script:

```python
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips

# Download from Pexels API
results = search_pexels_videos(query, PEXELS_KEY)

# Combine clips
clips = [VideoFileClip(p).subclipped(0, dur) for p in paths]
final = concatenate_videoclips(clips, method="compose")

# Add background music
audio = AudioFileClip(music_path).subclipped(0, final.duration)
audio = audio.with_volume_scaled(0.25)
final = final.with_audio(audio)

final.write_videofile("output.mp4", codec="libx264", audio_codec="aac", fps=24)
```

**MoviePy 2.x Changes:**
- Use `.subclipped(start, end)` NOT `.subclip(start, end)`
- Import: `from moviepy import VideoFileClip` NOT `from moviepy.editor import`

## Related Skills

- `content-engine` for script/copywriting
- `brand-voice` for voice consistency
