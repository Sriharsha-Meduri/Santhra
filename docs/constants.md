# Santhra - Constants and their provenance

This project makes a specific, testable claim: **only the network weights and a
small set of calibration parameters are learned from data. Every other number is
either a mathematical definition, a configuration/hyperparameter, or a hand-chosen
domain heuristic, and none of them are dressed up as "learned".**

Every decision-layer constant lives in one place, `backend/app/config.py` (the
fusion/decision section), so the whole policy is auditable at a glance. This
document records, for each constant, why it exists and how it is classified:

- **A - Learned from data** (fit by training/calibration on the dataset)
- **B - Derived mathematically** (a definition or a standard formula)
- **C - Configuration / hyperparameter** (a design choice or tunable)
- **D - Domain heuristic** (chosen by hand from domain knowledge, not fit)

## Learned from data (A)

| Thing | Where | Why it exists |
|---|---|---|
| CNN + autoencoder weights | `ml/checkpoints/model.pt`, `anomaly.pt` | trained by `ml/training/train.py` and `train_anomaly.py` |
| `class_temperature` (2.98) | `calibration.json` | fit on the validation split by minimising NLL (temperature scaling) |
| `issue_temperatures` (per issue) | `calibration.json` | one temperature per issue head, fit on validation |
| AE `clean_recon_mean` / `clean_recon_std` | `anomaly.pt` stats | measured reconstruction-error distribution on clean validation images; used to standardize the anomaly z-score |

These are the only values in the system fit from data.

## Derived mathematically (B)

| Constant | Value | Why |
|---|---|---|
| `IMAGENET_MEAN` / `IMAGENET_STD` | (0.485,0.456,0.406) / (0.229,0.224,0.225) | the standard ImageNet channel statistics required by the pretrained backbone |
| anomaly `z_score` | `(err - mean) / std` | textbook standardization against the clean distribution (the mean/std are the learned A values above) |
| per-issue `agreement` | `1 - |p_model - cv_severity|` | a definition of closeness between the two signals in `[0,1]` |
| `cv_score` erosion | `100 * prod(1 - w*severity)` | multiplicative composition so stacked defects compound; the weight `w` itself is a heuristic (below) |

## Configuration / hyperparameters (C)

| Constant | Value | Why |
|---|---|---|
| `MODEL_INPUT_SIZE` | 224 | MobileNetV3-Small's native input resolution |
| `ANOMALY_INPUT_SIZE` | 128 | autoencoder design choice (speed vs detail) |
| `CV_MAX_SIDE` | 1024 | caps classical-CV cost on large images |
| loss weights | class 1 / issues 1 / score 2 | training hyperparameter; the score head is upweighted because its MAE moved slowest |
| train/val/test split | 70 / 15 / 15 | a conventional split, applied at the **source-image** level to prevent leakage |
| `MAX_UPLOAD_SIZE_MB` / `MAX_PIXELS` / `MIN`,`MAX_DIMENSION` | 15 MB / 50 MP / 8 / 12000 | ingest safety limits |
| epochs / batch size / lr | see `ml/training/*` | standard training hyperparameters |

## Domain heuristics (D)

These are hand-chosen. They are gathered in `config.py` and documented here so
they are never mistaken for learned values. They encode a reasonable policy; they
were not tuned against the test set (that would leak), so they are deliberately
round, interpretable numbers.

| Constant | Value | Why this value |
|---|---|---|
| `ISSUE_ML_WEIGHT` / `ISSUE_CV_WEIGHT` | 0.55 / 0.45 | detection blends both signals, tilted slightly to the learned model, which generalizes better across content |
| `DETECT_THRESHOLD` | 0.45 | an issue is reported when the blended strength passes the midpoint; slightly below 0.5 so a strong single signal can still surface an issue the other missed |
| `SCORE_ML_WEIGHT` / `SCORE_CV_WEIGHT` | 0.5 / 0.5 | the overall score weights the learned and measured halves equally |
| `CV_SCORE_SEVERITY_WEIGHT` | 0.9 | a single maxed-out defect still leaves 10/100 of headroom rather than zeroing the score |
| `FUSED_SEVERITY_BANDS` | 0.88 / 0.74 / 0.60 | CRITICAL / HIGH / MEDIUM cut points on the fused strength |
| `AGREEMENT_HIGH` | 0.72 | signals "agree" when they are within ~0.28 of each other |
| `STRONG_DISAGREE` | 0.45 | a per-issue agreement below this flags the result for human review |
| `ISSUE_CONF_*` weights | 0.5 / 0.5 | per-issue confidence weighs agreement and strength equally |
| `CONF_*` weights | 0.5 / 0.3 / 0.2 | overall confidence favours detector agreement, then class margin, then anomaly consistency |
| `CONF_HIGH` / `CONF_MEDIUM` | 0.66 / 0.45 | bucket cut points for HIGH / MEDIUM / LOW confidence |
| `ANOMALY_SIGMOID_CENTER` | 2.0 | maps a 2-sigma reconstruction error to a score of 0.5 |
| `ANOMALY_DETECT` | 0.60 | flags a potential anomaly at ~2.4 sigma above the clean mean |
| `SCORE_BANDS` | 90 / 75 / 50 | EXCELLENT / ACCEPTABLE / DEGRADED / POTENTIALLY_DEFECTIVE band edges |
| quality-class labels | `n>=3 or max_sev>=0.75` | training-label rule in `degradations.py`: 3+ issues or one severe issue is POTENTIALLY_DEFECTIVE |
| degradation severity ranges | e.g. blur sigma 1.2-5.5, noise std 10-48, jpeg q 42-6 | define what "severity 0 -> 1" means for each synthetic degradation (`ml/datasets/degradations.py`); design choices, not measurements |

## How to change them safely

Because the heuristics are policy, not fit, they can be revised without
retraining: edit the value in `config.py`, and the fusion tests
(`backend/tests/test_cv_ml.py::test_fusion_is_hybrid_not_cnn_only` and the API
tests) will confirm the decision behaviour still holds. Changing a *learned*
value instead means re-running training or calibration.
