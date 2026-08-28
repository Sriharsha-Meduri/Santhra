# Santhra - ML pipeline

Reproducible, leakage-safe training for the multi-task image-quality model and
the clean-image anomaly autoencoder.

## Pipeline

```
prepare_clean_images.py   # download Imagenette-160, cap to 1200 clean PNGs
        │
build_dataset.py          # split SOURCES 70/15/15, THEN generate degraded
        │                 #   variants per split -> ml/data/manifest.json
train.py                  # multi-task MobileNetV3-Small (class + issues + score)
train_anomaly.py          # conv autoencoder on CLEAN images only
calibrate.py              # temperature scaling on val -> calibration.json
evaluate.py               # metrics on TEST split -> docs/evaluation.md
```

Run everything: `bash scripts/train.sh` (env: `MAX_SOURCES`, `EPOCHS`).

## Leakage prevention (why the numbers are trustworthy)

The **clean source images are split first**, and degraded variants are only ever
generated *within* a split. No source image - or any of its variants - can appear
in more than one split. `build_dataset.py` asserts the splits are disjoint. This
means the TEST metrics reflect generalisation to unseen *content*, not memorised
variants.

## Labels

* `quality_class` - ACCEPTABLE / DEGRADED / POTENTIALLY_DEFECTIVE (CrossEntropy)
* `issues` - 7-way multi-label (BCEWithLogits): blur, underexposure, overexposure,
  noise, low_contrast, compression, color_cast
* `score` - 0-100 regression (SmoothL1), each degradation multiplicatively erodes quality

## Degradations (deterministic, seeded, parameters stored)

gaussian/motion blur · gaussian/poisson noise · under/over-exposure ·
contrast reduction · JPEG compression · colour desaturation/cast · and
combinations (up to 3 groups). Every applied parameter is recorded in the
manifest (e.g. `blur_sigma`, `jpeg_quality`, `brightness_factor`).

Artifacts are written to `ml/data/` (git-ignored - regenerate with the scripts)
and checkpoints to `ml/checkpoints/` (committed so the app runs out of the box).
