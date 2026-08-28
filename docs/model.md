# Santhra - Model Card

`santhra-mtl-mobilenetv3s`, version 1.0.0. Framework: PyTorch 2.6.
The live values on this card are also served at `GET /api/v1/model/info`.

## Overview

A single lightweight multi-task CNN inspects image technical quality. One shared
backbone feeds three heads, so one forward pass answers three related questions
at once. A separate convolutional autoencoder models the clean-image
distribution for anomaly detection. Both are fused with a classical CV engine
(see [architecture.md](architecture.md)); this card covers the learned parts.

## Architecture

- **Backbone:** MobileNetV3-Small, pretrained on ImageNet, fine-tuned end to end.
  Chosen for a strong accuracy-to-compute ratio so the system runs on CPU.
- **Shared trunk:** global-pooled features (576-d) -> Linear 1024 -> Hardswish ->
  Dropout.
- **Heads:**
  - `quality_class` (3-way softmax): ACCEPTABLE / DEGRADED / POTENTIALLY_DEFECTIVE.
  - `issues` (7-way multi-label, `BCEWithLogitsLoss`): blur, underexposure,
    overexposure, noise, low_contrast, compression, color_cast.
  - `score` (single regression, 0-100): overall technical quality.
- **Input:** 224x224 RGB, ImageNet normalisation.
- **Anomaly model:** convolutional autoencoder at 128x128 trained only on clean
  images. The reconstruction error is standardized against the clean-image
  distribution (mean/std fit on clean validation images) to give a `z_score`.
  The surfaced `anomaly.score` in `[0, 1]` is a monotonic sigmoid of that
  z-score (centred at ~2 sigma) - an **uncalibrated** ranking of how unusual the
  reconstruction is, **not** a calibrated probability (there is no
  anomaly-labelled data to calibrate against). It is presented as a *potential*
  anomaly, never a confirmed defect.

Loss is a weighted sum with weights `{class: 1, issues: 1, score: 2}` (the score
head is upweighted because MAE moved slowest during training).

## Training data

Real natural images (Imagenette) are degraded with **deterministic, seeded**
synthetic recipes. Each degradation stores its own parameters, so every label is
exact rather than estimated:

- Gaussian and motion blur, Gaussian and Poisson noise, under/over-exposure,
  contrast reduction, JPEG compression, and colour distortion.
- Recipes are grouped so related issues share a generator, and each variant may
  stack up to a few operations to produce realistic mixed-defect images.
- Variant 0 of every source is guaranteed clean, giving the model genuine
  negative examples.

**Leakage prevention:** source images are split into train/val/test **first**
(70/15/15), and only then are degraded variants generated within each split. No
source image appears in more than one split, and the build script asserts this.
The test split is 540 variants from 180 sources the model never saw.

Labels: the 7 issue flags come directly from which recipes were applied; the
quality class and 0-100 score come from a documented function of the applied
degradations (`ml/datasets/degradations.py`), so scores erode multiplicatively as
defects stack.

## Training procedure

- Transfer learning from ImageNet weights, Adam, early stopping on a combined
  validation selection metric, best-checkpoint saving with full metadata.
- Fixed seeds; automatic mixed precision on GPU with a clean CPU fallback.
- Light train-time augmentation (horizontal flip) only, to avoid changing the
  very quality signals being measured.

## Calibration

Raw neural probabilities are overconfident, so the class head is **temperature
scaled** (temperature fit on the validation split by minimising NLL). Measured
effect on the validation split:

- Class NLL: 0.7193 -> **0.4281**
- Class ECE: 0.1238 -> **0.0217**

The fitted class temperature is 2.98. This is why the UI can honestly say
"HIGH / MEDIUM / LOW confidence" and surface an "uncertain, signals disagree"
state instead of a falsely sharp number.

## Results

Held-out **test** split (unseen sources). Full tables, confusion matrix and
failure cases are in [evaluation.md](evaluation.md).

| Metric | Value |
|---|---|
| Issue macro-F1 | 0.888 |
| Issue micro-F1 | 0.877 |
| Quality-class accuracy | 0.807 |
| Quality-score MAE | 10.27 / 100 |

Per-issue F1 ranges from 0.98 (blur, underexposure) down to 0.71 (color_cast).
Validation selection metrics stored in the checkpoint: issue macro-F1 0.9004,
class accuracy 0.8278, score MAE 10.379.

## Intended use and limits

**Intended:** automated first-pass screening of image *technical* quality with
explainable evidence, for triage and human review.

**Not intended:** confirming physical product defects, medical or forensic
decisions, or detecting arbitrary real-world defect categories the model was
never trained on. The anomaly signal is an uncalibrated score surfaced as a
*potential* anomaly, never a confirmed defect. Full discussion in
[limitations.md](limitations.md).

## Data, licensing & attribution

- **Source images:** [Imagenette](https://github.com/fastai/imagenette) (the
  160px variant), a subset of ImageNet curated by fast.ai. The images retain
  ImageNet's terms and are used here for **non-commercial research and
  educational** purposes only, solely to synthesize a labelled image-quality
  dataset. They are downloaded at build time and are not redistributed in this
  repository (`ml/data/` is git-ignored).
- **Pretrained weights:** MobileNetV3-Small ImageNet weights from
  `torchvision` (BSD-3-Clause), fine-tuned here.
- **Degradations and labels** are generated by this project's own code
  (`ml/datasets/degradations.py`); the resulting labels are exact functions of
  the applied operations, not third-party annotations.
- **Committed demo samples** do not use ImageNet at all: they are degraded
  versions of the freely-licensed scikit-image sample photographs (astronaut and
  rocket: public domain; chelsea: CC0), so they can be redistributed publicly.
  See `sample_images/ATTRIBUTION.md`.

## Versioning

The checkpoint stores `model_name`, `model_version`, `issue_types`,
`quality_classes`, `input_size`, `loss_weights`, backbone, framework, train
timestamp and validation metrics. The pipeline version and feature version are
tracked separately in `config.py` and returned on every analysis, so any stored
result can be traced to the exact code and weights that produced it.
