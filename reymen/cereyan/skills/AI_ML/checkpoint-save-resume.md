---
name: checkpoint-save-resume
description: Atomic, sharded checkpoints with full RNG capture so a killed run resumes mid-epoch with the same loss trajectory.
title: "Checkpoint Save Resume"
version: 1.0.0
phase: 19
lesson: 47
tags: [training, durability, resume, sharded-state]
category: checkpoint-save-resume
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI muhendisi |
| **Ne** | Atomic, sharded checkpoints with full RNG capture so a killed run resumes mid-epoch with the same loss trajectory. |
| **Nerede** | `ai\ecc\checkpoint-save-resume.md` |
| **Ne Zaman** | AI modeli secimi veya degerlendirmesi gerektiginde |
| **Neden** | Checkpoint Save Resume islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Atomic, sharded checkpoints with full RNG capture so a killed run resumes mid-epoch with the same loss trajectory. |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: AI muhendisi
Ne: Atomic, sharded checkpoints with full RNG capture so a killed run resumes mid-epoch with the same loss trajectory.
Nerede: `ai\ecc\checkpoint-save-resume.md`
Ne Zaman: AI modeli secimi veya degerlendirmesi gerektiginde
Neden: Checkpoint Save Resume islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


## When to use

Any training run longer than the wallclock cap of the cluster, any run that must survive a node reboot, any model too large for a single payload.

## Payload shape

```python
{
  "schema": "ckpt.v1",
  "model": model.state_dict(),
  "optimizer": opt.state_dict(),
  "scheduler": sched.state_dict(),
  "state": {"step": int, "epoch": int, "batch_in_epoch": int, "losses": [float, ...]},
  "rng": {"python": ..., "numpy": ..., "torch_cpu": ..., "torch_cuda": ...},
  "wall_saved_at": time.time(),
}
```

## Atomic save

1. Write the payload to a unique temp file in the same directory as the target.
2. `os.replace(tmp, target)` to swap atomically.
3. Never write directly to the target name.

## Sharded layout

- `model.shard-NNN.pt` per shard, round robin on keys or split by parameter group.
- `meta.pt` carries optimizer, scheduler, train state, RNG, and the shard manifest.
- `index.json` carries `sha256` for every shard and for `meta.pt`.
- Loader verifies every hash before merging.

## Mid-epoch resume

- Save `(epoch, batch_in_epoch)` next to `step`.
- Restore RNG state before the first batch of the resumed epoch.
- Fast-forward the generator past consumed batches.

## Failure modes

- Cross-device rename: not atomic, lose the previous file. Put temp in same directory.
- Forgetting RNG: resumed loss diverges from baseline. Run the demo's assertion.
- Forgetting optimizer state: next step lurches. Same diff blows up.
- Pruning the wrong checkpoint: keep last K plus best.
