"""🎬 Video araçları — yt-dlp + ffmpeg wrapper.

Video indirme (yt-dlp) ve dönüştürme/kesme (ffmpeg) için CLI sarmalayıcıları.
İkili dosyalar sistemde yoksa ``VideoToolError`` fırlatılır; ``check_available``
ile varlık kontrolü yapılabilir.

Örnek::

    from ReYMeN.video_tools import download, convert, probe
import logging
logger = logging.getLogger(__name__)

    info = download("https://youtube.com/watch?v=...", output="%(title)s.%(ext)s")
    convert("input.mp4", "output.mp3", format="mp3")
    meta = probe("video.mp4")
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

__all__ = [
    "VideoToolError",
    "VideoInfo",
    "FFmpegResult",
    "check_available",
    "ensure_tool",
    "download",
    "convert",
    "probe",
    "cut",
    "extract_audio",
]


# ---------------------------------------------------------------------------
# Hatalar
# ---------------------------------------------------------------------------
class VideoToolError(RuntimeError):
    """Video araçları hatası."""


# ---------------------------------------------------------------------------
# Varlık kontrolü
# ---------------------------------------------------------------------------
def _find_tool(name: str) -> str | None:
    """Sistemde bir CLI aracını arar."""
    return shutil.which(name)


def check_available() -> dict[str, bool]:
    """yt-dlp ve ffmpeg'in kurulu olup olmadığını döndürür."""
    return {
        "yt-dlp": _find_tool("yt-dlp") is not None,
        "ffmpeg": _find_tool("ffmpeg") is not None,
        "ffprobe": _find_tool("ffprobe") is not None,
    }


def ensure_tool(name: str) -> str:
    """Aracın yolunu döndürür; yoksa ``VideoToolError`` fırlatır."""
    path = _find_tool(name)
    if path is None:
        raise VideoToolError(
            f"'{name}' sistemde bulunamadı. Lütfen kurun: "
            f"{'pip install yt-dlp' if name == 'yt-dlp' else 'https://ffmpeg.org'}"
        )
    return path


# ---------------------------------------------------------------------------
# Veri yapıları
# ---------------------------------------------------------------------------
@dataclass
class VideoInfo:
    """İndirilen video bilgisi."""

    url: str
    title: str = ""
    filepath: str = ""
    duration: float = 0.0
    uploader: str = ""
    view_count: int = 0
    formats: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "filepath": self.filepath,
            "duration": self.duration,
            "uploader": self.uploader,
            "view_count": self.view_count,
            "formats": self.formats,
            "raw": self.raw,
        }


@dataclass
class FFmpegResult:
    """ffmpeg/ffprobe komut sonucu."""

    success: bool
    command: list[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "command": self.command,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


# ---------------------------------------------------------------------------
# yt-dlp: indirme
# ---------------------------------------------------------------------------
def download(
    url: str,
    *,
    output: str = "%(title)s.%(ext)s",
    output_dir: str | Path | None = None,
    format: str | None = None,
    audio_only: bool = False,
    extra_args: Sequence[str] | None = None,
    timeout: float | None = None,
) -> VideoInfo:
    """yt-dlp ile video indirir.

    Args:
        url: Video URL'si.
        output: Çıktı dosya şablonu (yt-dlp formatı).
        output_dir: Çıktı dizini (None ise mevcut dizin).
        format: Format seçimi (örn. "best", "bestvideo+bestaudio").
        audio_only: Sadece ses indir (mp3).
        extra_args: yt-dlp'ye ek argümanlar.
        timeout: Saniye cinsinden timeout.

    Returns:
        ``VideoInfo`` — indirilen video bilgisi.
    """
    ytdlp = ensure_tool("yt-dlp")

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_template = str(output_dir / output)
    else:
        output_template = output

    cmd: list[str] = [
        ytdlp,
        "--print-json",
        "--no-playlist",
        "-o", output_template,
    ]

    if audio_only:
        cmd += ["-x", "--audio-format", "mp3", "--audio-quality", "0"]
    elif format:
        cmd += ["-f", format]

    if extra_args:
        cmd += list(extra_args)

    cmd.append(url)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise VideoToolError(f"yt-dlp timeout ({timeout}s)") from e

    if result.returncode != 0:
        raise VideoToolError(
            f"yt-dlp başarısız (exit {result.returncode}): {result.stderr.strip()}"
        )

    # yt-dlp --print-json her satırda bir JSON yazar
    info_data: dict[str, Any] = {}
    for line in result.stdout.strip().splitlines():
        try:
            info_data = json.loads(line)
            break
        except json.JSONDecodeError:
            continue

    filepath = info_data.get("_filename", "") or info_data.get("filepath", "")
    if output_dir and filepath and not os.path.isabs(filepath):
        filepath = str(Path(output_dir) / filepath)

    return VideoInfo(
        url=url,
        title=info_data.get("title", ""),
        filepath=filepath,
        duration=float(info_data.get("duration", 0) or 0),
        uploader=info_data.get("uploader", ""),
        view_count=int(info_data.get("view_count", 0) or 0),
        formats=info_data.get("formats", []),
        raw=info_data,
    )


# ---------------------------------------------------------------------------
# ffprobe: meta veri
# ---------------------------------------------------------------------------
def probe(filepath: str | Path) -> dict[str, Any]:
    """ffprobe ile medya meta verilerini döndürür."""
    ffprobe = ensure_tool("ffprobe")
    cmd = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(filepath),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise VideoToolError(
            f"ffprobe başarısız: {result.stderr.strip()}"
        )
    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# ffmpeg: dönüştürme
# ---------------------------------------------------------------------------
def _run_ffmpeg(
    cmd: list[str],
    *,
    timeout: float | None = None,
) -> FFmpegResult:
    ffmpeg = ensure_tool("ffmpeg")
    full_cmd = [ffmpeg, "-y", *cmd]
    try:
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise VideoToolError(f"ffmpeg timeout ({timeout}s)") from e

    return FFmpegResult(
        success=result.returncode == 0,
        command=full_cmd,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def convert(
    input_path: str | Path,
    output_path: str | Path,
    *,
    format: str | None = None,
    video_codec: str | None = None,
    audio_codec: str | None = None,
    bitrate: str | None = None,
    extra_args: Sequence[str] | None = None,
    timeout: float | None = None,
) -> FFmpegResult:
    """ffmpeg ile video/ses dönüştürme.

    Args:
        input_path: Girdi dosyası.
        output_path: Çıktı dosyası (uzantı formatı belirler).
        format: Çıktı formatı (örn. "mp3", "mp4").
        video_codec: Video kodeği (örn. "libx264").
        audio_codec: Ses kodeği (örn. "aac", "libmp3lame").
        bitrate: Bitrate (örn. "192k").
        extra_args: ffmpeg'ye ek argümanlar.
        timeout: Saniye cinsinden timeout.

    Returns:
        ``FFmpegResult``.
    """
    cmd: list[str] = ["-i", str(input_path)]

    if video_codec:
        cmd += ["-c:v", video_codec]
    if audio_codec:
        cmd += ["-c:a", audio_codec]
    if bitrate:
        cmd += ["-b:a", bitrate]
    if format:
        cmd += ["-f", format]
    if extra_args:
        cmd += list(extra_args)

    cmd.append(str(output_path))

    result = _run_ffmpeg(cmd, timeout=timeout)
    if not result.success:
        raise VideoToolError(
            f"ffmpeg dönüştürme başarısız (exit {result.returncode}): "
            f"{result.stderr.strip()}"
        )
    return result


def extract_audio(
    input_path: str | Path,
    output_path: str | Path,
    *,
    format: str = "mp3",
    bitrate: str = "192k",
    timeout: float | None = None,
) -> FFmpegResult:
    """Videodan ses çıkarır (kısayol)."""
    return convert(
        input_path,
        output_path,
        format=format,
        video_codec="none",
        audio_codec="libmp3lame" if format == "mp3" else None,
        bitrate=bitrate,
        timeout=timeout,
    )


def cut(
    input_path: str | Path,
    output_path: str | Path,
    *,
    start: str,
    duration: str | None = None,
    end: str | None = None,
    copy_codecs: bool = True,
    timeout: float | None = None,
) -> FFmpegResult:
    """Videodan belirli bir bölümü keser.

    Args:
        input_path: Girdi dosyası.
        output_path: Çıktı dosyası.
        start: Başlangıç zamanı (örn. "00:01:30" veya "90").
        duration: Süre (örn. "00:00:30"). ``end`` ile birlikte kullanılamaz.
        end: Bitiş zamanı. ``duration`` ile birlikte kullanılamaz.
        copy_codecs: Hızlı kesim için kodek kopyalama (yeniden kodlama yok).
        timeout: Saniye cinsinden timeout.
    """
    if duration and end:
        raise ValueError("'duration' ve 'end' birlikte kullanılamaz")

    cmd: list[str] = ["-ss", str(start)]
    if end:
        cmd += ["-to", str(end)]
    elif duration:
        cmd += ["-t", str(duration)]

    cmd += ["-i", str(input_path)]

    if copy_codecs:
        cmd += ["-c", "copy"]

    cmd.append(str(output_path))

    result = _run_ffmpeg(cmd, timeout=timeout)
    if not result.success:
        raise VideoToolError(
            f"ffmpeg kesim başarısız (exit {result.returncode}): "
            f"{result.stderr.strip()}"
        )
    return result