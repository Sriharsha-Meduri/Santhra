# Santhra - Limitations

Stating these plainly is part of the design. A quality tool that hides its own
failure modes cannot be trusted for triage.

## Training distribution

- The model is trained on **synthetic degradations of natural photographs**
  (Imagenette). The recipes (blur, noise, exposure, contrast, compression,
  colour) are representative but not exhaustive. Real-world degradations from a
  specific camera, sensor, or pipeline may look different and can be scored less
  accurately than the held-out synthetic test set suggests.
- Content is general natural imagery. Specialised domains (medical scans,
  satellite, microscopy, documents) are out of distribution and would need
  their own data and retraining.

## Known weaker signals

- **Colour cast** is the weakest issue (test F1 0.71). Mild, globally consistent
  casts overlap with legitimate artistic white-balance choices, so both the
  model and the CV metric are less certain here.
- **Compression** (F1 0.81) is reliable for visible blocking but can miss light
  compression that leaves little 8x8 structure.
- **Under/over-exposure** share one recipe group and have smaller support, so
  their metrics are noisier than the high-support issues.
- The 3-way **quality class** is strong on the ACCEPTABLE and
  POTENTIALLY_DEFECTIVE ends but weaker in the middle DEGRADED band (F1 0.65),
  where borderline images are genuinely ambiguous. The continuous 0-100 score
  (MAE ~10) is the better signal for borderline cases and is what the UI leads
  with.

## Anomaly detection

- The autoencoder is trained only on clean images and flags reconstruction
  outliers. It answers "does this look unlike normal clean images?" not "is
  there a defect here?". It is surfaced as a **potential anomaly**, and a
  clean/anomaly conflict is one of the triggers for the "review recommended"
  flag rather than a verdict on its own.
- The `anomaly.score` is an **uncalibrated** ranking (a monotonic transform of
  the reconstruction-error z-score), not a calibrated probability. There is no
  anomaly-labelled data to calibrate it against, so only its ordering and the
  detection cutoff (~2.4 sigma) are meaningful, not the absolute value.

## Localisation

- Grad-CAM shows where the network attended, which is correlated with, but not
  identical to, the physical location of a defect. The CV problem-region map is
  a more literal per-pixel signal for local blur, clipping and noise. The UI
  shows both and does not claim pixel-perfect defect segmentation.

## System scope

- Single-image analysis. There is no cross-image batch scoring beyond the
  convenience batch endpoint, and no video.
- SQLite is used for portability. It is fine for this scale; a high-throughput
  deployment would move to PostgreSQL (the ORM is already compatible) and an
  object store for media.
- Latency figures (~0.4 s/image) are CPU, warm. The first request after a cold
  start is slightly slower despite startup warming.

## What would improve it

- Real degraded images with human quality labels, to complement the synthetic
  set and close the synthetic-to-real gap.
- Per-issue calibration validated on real data (issue heads currently use a
  shared temperature).
- A larger backbone where latency budget allows, and per-issue localisation
  heads for true defect segmentation.
