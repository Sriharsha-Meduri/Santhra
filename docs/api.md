# Santhra - API Reference

Base URL (local): `http://localhost:8000`. Interactive docs are served at
`/docs` (Swagger) and `/redoc`. Every response carries an `X-Request-ID` header,
also emitted in the logs, for tracing.

All endpoints are versioned under `/api/v1` except the two liveness routes
(`/` and `/health`).

## Conventions

- Errors return a structured body: `{"error": "<code>", "detail": "<message>",
  "request_id": "<id>"}` with an appropriate HTTP status. The server never
  returns an unstructured 500 for a bad image.
- Uploads are multipart form-data under the field name `file`. Max size defaults
  to 15 MB (`MAX_UPLOAD_SIZE_MB`). Accepted formats: JPEG, PNG, BMP, WEBP, TIFF.

---

## GET `/health`

Real readiness check. Returns 200 when healthy.

```json
{
  "status": "healthy",
  "model_loaded": true,
  "anomaly_model_loaded": true,
  "database": "connected",
  "device": "cpu",
  "model": { "name": "santhra-mtl-mobilenetv3s", "version": "1.0.0" },
  "version": "1.0.0"
}
```

---

## POST `/api/v1/analyze`

Analyse one image. `multipart/form-data`, field `file`.

```bash
curl -F "file=@sample.jpg" http://localhost:8000/api/v1/analyze
```

**200** returns one document. Top-level fields:

| Field | Type | Origin | Notes |
|---|---|---|---|
| `id` | str | - | UUID, also the media folder name |
| `created_at` | str | - | UTC ISO-8601, `Z` suffixed |
| `filename`, `format` | str | - | sanitised name, detected format |
| `image` | object | measured | width, height, channels, megapixels, aspect_ratio, file_size_kb |
| `quality_score` | int | **fused** | 0-100 |
| `quality_label` | str | **fused** | EXCELLENT / ACCEPTABLE / DEGRADED / POTENTIALLY_DEFECTIVE |
| `quality_class` | str | learned | 3-way class head |
| `class_probabilities` | object | learned | calibrated softmax |
| `overall_confidence` | str | **fused** | HIGH / MEDIUM / LOW |
| `overall_confidence_value` | float | **fused** | 0-1 |
| `review_recommended` | bool | **fused** | see `review_reasons` |
| `review_reasons` | list[str] | **fused** | why review was flagged |
| `issues` | list | **fused** | per-issue verdicts (below) |
| `detected_issue_types` | list[str] | **fused** | convenience list |
| `dimensions` | object | measured | per-dimension 0-100 (sharpness, exposure, noise, contrast, colour, integrity) |
| `statistics` | object | measured | raw interpretable CV metrics |
| `signal_agreement` | object | **fused** | AI vs CV vs anomaly agreement |
| `anomaly` | object | learned | `detected`, `label`, `score`, `z_score`, `recon_error` (see note) |
| `integrity` | object | measured | `score` (0-100), `severely_degraded` (bool), `entropy`; flags corruption / severe degradation |
| `explainability` | object | mixed | heatmaps, forensics, narrative (below) |
| `model_info` | object | - | model/pipeline versions, device, sub-scores |
| `analysis_time_ms` | float | - | server processing time |

Each entry of `issues[]`:

```json
{
  "type": "blur",
  "detected": true,
  "severity": "MEDIUM",
  "severity_value": 0.55,
  "confidence": 0.70,
  "ml_probability": 0.96,
  "cv_severity": 0.40,
  "agreement": 0.44,
  "evidence": { "laplacian_variance": 63.65, "edge_density": 0.0009 }
}
```

`evidence` is an object mapping the relevant CV metric names to their measured
values (not a string).

`explainability` contains: `primary_issue`, `heatmap` (Grad-CAM overlay as a
data URL) and `heatmap_method`, `problem_regions` (CV overlay) and
`problem_method`, `forensics` (observed signal vs learned expectation cards),
`evidence_cards`, and a plain-language `narrative`.

The `anomaly.score` is an **uncalibrated** value in `[0, 1]` (a monotonic
sigmoid of `z_score`, the reconstruction error standardized against the
clean-image distribution). It ranks how far above normal the reconstruction
error is; it is **not** a calibrated probability. `detected` is `score >= 0.60`
(about 2.4 sigma), surfaced as a *potential* anomaly.

**Errors:** 415 unsupported format, 422 undecodable/invalid image, 413 too large.

---

## POST `/api/v1/analyze/batch`

Analyse several images in one call (form field `files`, repeated). Returns a
list of per-file results, each either an analysis document or a structured error,
so one bad file does not fail the batch.

---

## GET `/api/v1/analyses`

List stored analyses. Query params: `limit`, `offset`, `label`, `search`,
`sort` (`created_at` | `quality_score` | `filename`), `order` (`asc` | `desc`).

```json
{ "items": [ { "id": "...", "created_at": "...Z", "filename": "blurry.jpg",
  "quality_score": 63, "quality_label": "DEGRADED", "primary_issue": "blur",
  "review_recommended": true, "thumbnail_url": "/media/<id>/thumb.png" } ],
  "total": 3, "limit": 20, "offset": 0 }
```

## GET `/api/v1/analyses/{id}`

Full stored detail for one analysis. **404** if not found.

## DELETE `/api/v1/analyses/{id}`

Delete one analysis and its media folder. **204** on success, **404** if absent.

---

## GET `/api/v1/model/info`

Live model metadata (identity, input resolution, classes, issue types,
framework, backbone, loss weights, train timestamp, validation metrics, device,
load flags, calibration flag). Powers the Model Card page.

## GET `/api/v1/statistics`

Aggregate dashboard numbers.

```json
{ "total": 4, "average_score": 49.5,
  "by_label": { "EXCELLENT": 1, "DEGRADED": 1, "POTENTIALLY_DEFECTIVE": 2 },
  "review_rate": 0.5 }
```

---

## Media

Rendered PNGs are served as static files at `/media/<id>/<name>.png`
(thumbnail, heatmap, problem map). Binary image data is never stored in the
database.
