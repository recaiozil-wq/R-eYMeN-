
> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Windows Automation_Camera Capture |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: camera-capture-camera-capture
description: Capture video from webcam on Windows using Python + OpenCV. Use when user asks for camera recording, webcam capture, video from camera, or "kameradan video çek".
title: "Camera Capture"

audience: user
tags: [automation, camera, windows]
category: windows-automation---

# Camera Capture

Record video directly from a connected webcam on Windows without relying on ffmpeg PATH availability.

## When to Use

- "kameradan video çek", "kamera kaydı yap", "webcam kaydı"
- "10 saniye kamera videosu", "camera record 10s"
- Any request to capture live video from a physical camera

## Preferred Method: Python + OpenCV

Avoids ffmpeg PATH issues and PowerShell encoding pitfalls.

### Dependencies

- Python 3.x
- `opencv-python-headless` (preferred) or `opencv-python`

Install if missing:
```bash
pip install opencv-python-headless
```

### Reusable Script

Use `scripts/cam_capture_10s.py`. It captures N seconds from camera index 0 using DirectShow backend on Windows, outputs MP4.

Key parameters:
- Camera index: usually 0 (first camera)
- Backend: `cv2.CAP_DSHOW` for Windows stability
- Codec: `mp4v` (widely compatible without ffmpeg)
- Output: default to `C:\Users\<user>\Desktop\kamera_kaydi.mp4`

### Usage

```bash
python scripts/cam_capture_10s.py --output "C:\path\to\video.mp4" --seconds 10
```

## Fallback: FFmpeg DirectShow

If Python/OpenCV fails and ffmpeg is in PATH:
```bash
ffmpeg -f dshow -i video="Camera Name" -t 10 -vcodec libx264 -acodec aac output.mp4
```

List devices first:
```bash
ffmpeg -f dshow -list_devices true -i dummy
```

## Pitfalls

- **Turkish chars in PowerShell scripts**: File saving with UTF-8 BOM or console encoding can garble Turkish characters. Prefer ASCII-only PowerShell scripts or Python to avoid encoding errors.
- **FFmpeg not in PATH**: Even if installed, Git Bash/MSYS may not see it. Use full path or Python fallback.
- **Camera permission**: Windows may block camera access. If `cap.isOpened()` fails, check Windows Settings > Privacy > Camera.
- **Multiple cameras**: If index 0 is wrong, iterate 0-5 to find the working camera.

## Verification

After capture, confirm file exists and has non-zero size. Report output path and resolution.
