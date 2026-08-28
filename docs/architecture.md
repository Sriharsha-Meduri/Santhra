# Santhra - Architecture

Santhra answers six questions about any image: **what** is wrong, **how
severe**, **how confident** the system is, **where** the problem is, **why** the
verdict was reached, and **how reliable** that verdict is. It does this by
combining a learned model with a classical computer-vision engine and reconciling
the two in a transparent fusion step.

## 1. The hybrid-intelligence idea

A single learned classifier is a black box: it emits probabilities with no
traceable reason. A pure CV pipeline is transparent but brittle and cannot learn
what "degraded" looks like across many images. Santhra runs **both** and
treats them as two independent opinions:

```
                        ┌──────────────────────────┐
                        │        Input image        │
                        └────────────┬─────────────┘
              ┌──────────────────────┼──────────────────────┐
              ▼                      ▼                      ▼
   ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
   │  Learned model     │  │  CV feature engine │  │  Anomaly auto-     │
   │  MobileNetV3-Small │  │  OpenCV / skimage  │  │  encoder (clean    │
   │  3 heads:          │  │  measured metrics: │  │  distribution)     │
   │  class / issues /  │  │  sharpness, expo., │  │  reconstruction    │
   │  0-100 score       │  │  noise, contrast…  │  │  residual + z      │
   └─────────┬─────────┘  └─────────┬─────────┘  └─────────┬─────────┘
             │  calibrated probs      │  severities [0,1]     │  anomaly score
             └──────────────┬────────┴───────────┬───────────┘
                            ▼                    ▼
                  ┌────────────────────────────────────┐
                  │           Fusion engine             │
                  │  per-issue: detected / severity /   │
                  │  confidence / agreement / evidence  │
                  │  quality score 0-100, review flag   │
                  └───────────────────┬────────────────┘
                                      ▼
                  ┌────────────────────────────────────┐
                  │        Explainability layer         │
                  │  Grad-CAM overlay, CV problem-region │
                  │  map, forensics cards, narrative    │
                  └────────────────────────────────────┘
```

Every number the UI shows is tagged by origin: **measured** (CV), **learned**
(model), or **fused** (a decision that combined both). That separation is the
core design constraint, not a presentation detail.

## 2. Request flow (`POST /api/v1/analyze`)

1. **Ingress** (`api/routes_analysis.py`) reads the upload with a hard size
   guard, then hands the bytes to `services/analysis_service.py`.
2. **Decode & validate** (`core/security.py`) sniffs magic bytes, decodes with
   OpenCV and a PIL fallback, and rejects anything that is not a real image or
   is outside the min/max dimension bounds. Structured errors, never a crash.
3. **CV feature engine** (`cv/*`) computes interpretable metrics: Laplacian
   variance and Tenengrad for sharpness, luminance histogram statistics and clip
   fractions for exposure, wavelet sigma for noise, RMS for contrast, 8x8 DCT
   blockiness for compression, HSV/LAB statistics for colour, entropy and
   constant-row detection for corruption. `cv/reference.py` maps each raw metric
   to a documented severity in `[0, 1]`.
4. **Learned inference** (`ml/inference.py`) runs the multi-task CNN once,
   applies temperature-scaled calibration, and returns class probabilities,
   per-issue probabilities, and a 0-100 score. The autoencoder produces a
   reconstruction residual and z-score.
5. **Fusion** (`services/fusion_service.py`) combines the two opinions with fixed,
   documented weights (no magic numbers scattered in code) into per-issue
   verdicts, an overall score and band, confidence, and a review flag.
6. **Explainability** (`services/explainability_service.py`) builds a Grad-CAM
   heatmap, a CV problem-region overlay, forensics cards (observed signal vs
   learned expectation), evidence lines, and a plain-language narrative.
7. **Persist** (`db/*`) writes the structured result to SQLite. Rendered PNGs
   (thumbnail, heatmap, problem map) are written to disk under `media/<id>/`,
   never stored as binary blobs in the database.
8. **Respond** with a single typed JSON document (`schemas/analysis.py`).

Warm CPU latency is roughly **0.4 s** per image (measured in the running app).

## 3. Fusion rules (centralised, in `fusion_service.py`)

| Constant | Value | Meaning |
|---|---|---|
| `ISSUE_ML_WEIGHT` / `ISSUE_CV_WEIGHT` | 0.55 / 0.45 | per-issue detection blend |
| `DETECT_THRESHOLD` | 0.45 | fused score above which an issue is reported |
| `SCORE_ML_WEIGHT` / `SCORE_CV_WEIGHT` | 0.5 / 0.5 | overall 0-100 score blend |
| `AGREEMENT_HIGH` | 0.72 | `1 - |ml - cv|` above this means the signals agree |
| `STRONG_DISAGREE` | 0.45 | per-issue agreement below this flags review |
| `ANOMALY_DETECT` | 0.60 | anomaly-score cutoff (~2.4 sigma recon error) |
| `CV_SCORE_SEVERITY_WEIGHT` | 0.9 | CV score erosion per issue (below) |

Every decision constant (these plus the severity cut points, confidence-blend
weights, and anomaly cutoff) is defined in one place, `config.py`, and imported
by `fusion_service.py`. Each one is classified and justified in
[constants.md](constants.md): only the network weights and the calibration
temperatures are learned; the rest are configuration or hand-chosen heuristics,
and none are presented as learned. The CV half of the score erodes
multiplicatively per detected issue:
`cv_score = 100 * product(1 - CV_SCORE_SEVERITY_WEIGHT * severity)`.

- **Per-issue severity** is bucketed into `LOW / MEDIUM / HIGH / CRITICAL` from
  the fused strength.
- **Confidence** = `0.5 * detector-agreement + 0.3 * class-margin +
  0.2 * (1 - anomaly-conflict)`, bucketed HIGH/MEDIUM/LOW.
- **Review recommended** trips when confidence is LOW, when the model and CV
  disagree strongly on a detected issue, or when the autoencoder flags an anomaly
  the classifier called clean. The reasons are returned verbatim, so the flag is
  never unexplained.
- **Quality score** is `0.5 * model_score + 0.5 * cv_score`, mapped to a band:
  90-100 EXCELLENT, 75-89 ACCEPTABLE, 50-74 DEGRADED, 0-49 POTENTIALLY_DEFECTIVE.

## 4. Backend layout

```
backend/app
├── api/            HTTP routes (health, analyze, history, model, statistics)
├── cv/             classical feature engine (one module per signal family)
├── ml/             model definition, preprocessing, inference, calibration
├── services/       orchestration: inference, features, fusion, explainability
├── core/           errors, logging, security, time helpers
├── db/             SQLAlchemy models, repository, session
├── schemas/        Pydantic v2 request/response contracts
├── config.py       single source for sizes, bands, versions, and every
│                    fusion/decision threshold (see docs/constants.md)
└── main.py         app factory: middleware, request-id, error handlers, startup
```

The model is loaded exactly once (a locked singleton in
`services/inference_service.py`) and warmed on startup, so the first request is
not penalised.

## 5. Frontend

React + Vite + TypeScript + Tailwind, with Recharts for the radar and gauges.
The dev server and the production nginx image both proxy `/api`, `/media` and
`/health` to the backend, so the browser only ever talks to one origin and there
is no CORS in normal operation. The UI stages the analysis as a pipeline, then
renders the score gauge, per-issue cards, an image inspector (original / AI
heatmap / CV problem regions), the signal-agreement panel, forensics, the "why"
narrative, and the raw CV statistics.

## 6. Deployment

`docker compose up --build` starts two services: the FastAPI backend
(CPU PyTorch) and an nginx container serving the built frontend and proxying to
the backend. Volumes persist the SQLite database and the media directory. See
the root `README.md` for commands.

See also: [model.md](model.md), [evaluation.md](evaluation.md),
[api.md](api.md), [limitations.md](limitations.md).
