---
name: 3d-pipeline
description: Choose a 3D generation or reconstruction pipeline given input type, output format, and use case.
title: "3D Pipeline"
version: 1.0.0
phase: 8
lesson: 12
tags: [3d, gaussian-splatting, nerf, mesh]
category: 3d-pipeline
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ML/Veri bilimci |
| **Ne** | Choose a 3D generation or reconstruction pipeline given input type, output format, and use case. |
| **Nerede** | `mlops\architecture\3d-pipeline.md` |
| **Ne Zaman** | ML modeli egitimi veya deploy gerektiginde |
| **Neden** | 3D Pipeline islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Choose a 3D generation or reconstruction pipeline given input type, output format, and use case. |
| **Nerede?** | architecture/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: ML/Veri bilimci
Ne: Choose a 3D generation or reconstruction pipeline given input type, output format, and use case.
Nerede: `mlops\architecture\3d-pipeline.md`
Ne Zaman: ML modeli egitimi veya deploy gerektiginde
Neden: 3D Pipeline islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given inputs (text prompt / one image / few images / photo capture / video), target output (mesh / Gaussian splat / NeRF / point cloud), and use case (real-time render, game engine, AR / VR, cinematic), output:

1. Pipeline. (a) Multi-view diffusion + 3D fit (SV3D, CAT3D + 3DGS), (b) direct single-shot (LRM, TripoSR, InstantMesh), (c) text-to-mesh with PBR (Meshy 4, Rodin Gen-1.5, Hunyuan3D 2.0), (d) photo capture + 3DGS (Gsplat, Postshot, Scaniverse).
2. Base model + hosting. Named model + open / hosted. Include license relevance for commercial use.
3. Iteration budget. Expected time to first output, iteration cost, refinement strategy.
4. Topology + materials. Remesh pass needed? PBR channel requirements (albedo, roughness, metallic, normal)? UV layout automated or manual?
5. Eval. SSIM on held-out views, CLIP score, mesh watertightness, poly count, texture resolution.
6. Platform target. Unity / Unreal / Blender / web (three.js / Babylon) / AR (USDZ / glb).

Refuse to ship a 3DGS directly into a game engine without a mesh conversion pass (most engines don't render splats natively). Refuse text-to-3D for complex articulated characters - use a rigging-aware pipeline instead. Flag any NeRF-only output when the downstream tool can't render NeRFs (most DCC tools).
