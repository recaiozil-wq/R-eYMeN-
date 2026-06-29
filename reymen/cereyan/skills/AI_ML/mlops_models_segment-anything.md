---

name: segment-anything-model
description: "SAM: zero-shot image segmentation via points, boxes, masks."
title: "Segment Anything Model"
version: 1.0.0
author: Orchestra Research
license: MIT
dependencies: [segment-anything, transformers>=4.30.0, torch>=1.7.0]
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Multimodal, Image Segmentation, Computer Vision, SAM, Zero-Shot]
category: mlops
audience: user
tags: [ai, machine-learning, mlops, model]

---


> **Kategori:** mlops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | SAM: zero-shot image segmentation via points, boxes, masks. |
| **Nerede?** | mlops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Segment Anything

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Segment Anything Model (SAM) | `references/segment-anything-model-sam.md` |
| When to use SAM | `references/when-to-use-sam.md` |
| Quick start | `references/quick-start.md` |
| From GitHub | `references/from-github.md` |
| Optional dependencies | `references/optional-dependencies.md` |
| Or use HuggingFace transformers | `references/or-use-huggingface-transformers.md` |
| ViT-H (largest, most accurate) - 2.4GB | `references/vit-h-largest-most-accurate-2-4gb.md` |
| ViT-L (medium) - 1.2GB | `references/vit-l-medium-1-2gb.md` |
| ViT-B (smallest, fastest) - 375MB | `references/vit-b-smallest-fastest-375mb.md` |
| Load model | `references/load-model.md` |
| Create predictor | `references/create-predictor.md` |
| Set image (computes embeddings once) | `references/set-image-computes-embeddings-once.md` |
| Predict with point prompts | `references/predict-with-point-prompts.md` |
| Select best mask | `references/select-best-mask.md` |
| Load model and processor | `references/load-model-and-processor.md` |
| Process image with point prompt | `references/process-image-with-point-prompt.md` |
| Generate masks | `references/generate-masks.md` |
| Post-process masks to original size | `references/post-process-masks-to-original-size.md` |
| Core concepts | `references/core-concepts.md` |
| Interactive segmentation | `references/interactive-segmentation.md` |
| Single foreground point | `references/single-foreground-point.md` |
| Multiple points (foreground + background) | `references/multiple-points-foreground-background.md` |
| Bounding box [x1, y1, x2, y2] | `references/bounding-box-x1-y1-x2-y2.md` |
| Box + points for precise control | `references/box-points-for-precise-control.md` |
| Initial prediction | `references/initial-prediction.md` |
| Refine with additional point using previous mask | `references/refine-with-additional-point-using-previous-mask.md` |
| Automatic mask generation | `references/automatic-mask-generation.md` |
| Create generator | `references/create-generator.md` |
| Generate all masks | `references/generate-all-masks.md` |
| - point_coords: generating point | `references/point_coords-generating-point.md` |
| Sort by area (largest first) | `references/sort-by-area-largest-first.md` |
| Filter by predicted IoU | `references/filter-by-predicted-iou.md` |
| Filter by stability score | `references/filter-by-stability-score.md` |
| Batched inference | `references/batched-inference.md` |
| Process multiple images efficiently | `references/process-multiple-images-efficiently.md` |
| Process multiple prompts efficiently (one image encoding) | `references/process-multiple-prompts-efficiently-one-image-encoding.md` |
| Batch of point prompts | `references/batch-of-point-prompts.md` |
| ONNX deployment | `references/onnx-deployment.md` |
| Load ONNX model | `references/load-onnx-model.md` |
| Run inference (image embeddings computed separately) | `references/run-inference-image-embeddings-computed-separately.md` |
| Common workflows | `references/common-workflows.md` |
| Load model | `references/load-model.md` |
| Foreground point | `references/foreground-point.md` |
| Display best mask | `references/display-best-mask.md` |
| Create RGBA output | `references/create-rgba-output.md` |
| Process medical images (grayscale to RGB) | `references/process-medical-images-grayscale-to-rgb.md` |
| Segment region of interest | `references/segment-region-of-interest.md` |
| Output format | `references/output-format.md` |
| SamAutomaticMaskGenerator output | `references/samautomaticmaskgenerator-output.md` |
| Encode mask to RLE | `references/encode-mask-to-rle.md` |
| Decode RLE to mask | `references/decode-rle-to-mask.md` |
| Performance optimization | `references/performance-optimization.md` |
| Use smaller model for limited VRAM | `references/use-smaller-model-for-limited-vram.md` |
| Clear CUDA cache between large batches | `references/clear-cuda-cache-between-large-batches.md` |
| Use half precision | `references/use-half-precision.md` |
| Reduce points for automatic generation | `references/reduce-points-for-automatic-generation.md` |
| Export with --return-single-mask for faster inference | `references/export-with-return-single-mask-for-faster-inference.md` |
| Common issues | `references/common-issues.md` |
| References | `references/references.md` |
| Resources | `references/resources.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
