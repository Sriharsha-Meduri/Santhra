"""API-level tests: health, analysis, validation, persistence, batch."""
from __future__ import annotations

from conftest import make_image


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "healthy"
    assert j["model_loaded"] is True
    assert j["database"] == "connected"


def test_analyze_valid_image(client):
    r = client.post("/api/v1/analyze",
                    files={"file": ("blurry.jpg", make_image("blurry"), "image/jpeg")})
    assert r.status_code == 200
    j = r.json()
    assert 0 <= j["quality_score"] <= 100
    assert j["quality_label"] in {"EXCELLENT", "ACCEPTABLE", "DEGRADED", "POTENTIALLY_DEFECTIVE"}
    assert j["overall_confidence"] in {"HIGH", "MEDIUM", "LOW"}
    assert len(j["issues"]) == 7
    for iss in j["issues"]:
        assert 0.0 <= iss["confidence"] <= 1.0
        assert 0.0 <= iss["ml_probability"] <= 1.0
        assert iss["severity"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        assert isinstance(iss["evidence"], dict)          # evidence is an object, not a string
    # semantic: a heavily blurred image must actually be flagged as blurry
    blur = next(i for i in j["issues"] if i["type"] == "blur")
    assert blur["detected"] is True
    assert "blur" in j["detected_issue_types"]
    assert j["explainability"]["heatmap"].startswith("data:image")
    assert set(j["dimensions"]) == {"sharpness", "exposure", "noise", "contrast", "color", "integrity"}
    assert j["analysis_time_ms"] > 0
    # anomaly is an uncalibrated score in [0,1] (no "probability" field)
    an = j["anomaly"]
    assert set(an) == {"detected", "label", "score", "z_score", "recon_error"}
    assert 0.0 <= an["score"] <= 1.0
    # corruption / severe-degradation capability is surfaced
    integ = j["integrity"]
    assert set(integ) == {"score", "severely_degraded", "entropy"}
    assert isinstance(integ["severely_degraded"], bool)


def test_reject_oversized_upload(client):
    # size guard runs before decoding, so arbitrary bytes over the cap -> 413
    payload = b"\xff\xd8\xff" + b"\x00" * (16 * 1024 * 1024)
    r = client.post("/api/v1/analyze",
                    files={"file": ("huge.jpg", payload, "image/jpeg")})
    assert r.status_code == 413
    assert r.json()["error"] == "file_too_large"


def test_reject_empty_upload(client):
    r = client.post("/api/v1/analyze",
                    files={"file": ("empty.jpg", b"", "image/jpeg")})
    assert r.status_code == 422
    assert r.json()["error"] == "invalid_image"


def test_statistics(client):
    client.post("/api/v1/analyze",
                files={"file": ("s.jpg", make_image("noisy"), "image/jpeg")})
    j = client.get("/api/v1/statistics").json()
    assert j["total"] >= 1
    assert set(j) >= {"total", "average_score", "by_label", "review_rate"}
    assert 0.0 <= j["review_rate"] <= 1.0


def test_history_label_filter(client):
    client.post("/api/v1/analyze",
                files={"file": ("f.jpg", make_image("blurry"), "image/jpeg")})
    r = client.get("/api/v1/analyses", params={"label": "POTENTIALLY_DEFECTIVE"}).json()
    assert all(it["quality_label"] == "POTENTIALLY_DEFECTIVE" for it in r["items"])


def test_reject_unsupported_format(client):
    r = client.post("/api/v1/analyze",
                    files={"file": ("note.txt", b"just text, not an image", "text/plain")})
    assert r.status_code == 415
    assert r.json()["error"] == "unsupported_format"


def test_reject_corrupted_image(client):
    corrupted = b"\xff\xd8\xff" + b"\x00" * 256          # JPEG magic, garbage body
    r = client.post("/api/v1/analyze",
                    files={"file": ("bad.jpg", corrupted, "image/jpeg")})
    assert r.status_code == 422
    assert r.json()["error"] == "invalid_image"


def test_persistence_and_history(client):
    r = client.post("/api/v1/analyze",
                    files={"file": ("clean.png", make_image("clean", ".png"), "image/png")})
    aid = r.json()["id"]
    lst = client.get("/api/v1/analyses").json()
    assert lst["total"] >= 1
    detail = client.get(f"/api/v1/analyses/{aid}")
    assert detail.status_code == 200
    assert detail.json()["id"] == aid
    assert client.delete(f"/api/v1/analyses/{aid}").status_code == 204
    assert client.get(f"/api/v1/analyses/{aid}").status_code == 404


def test_model_info(client):
    j = client.get("/api/v1/model/info").json()
    assert len(j["issue_types"]) == 7
    assert j["model_loaded"] is True
    assert j["validation_metrics"]["issue_macro_f1"] > 0.5


def test_batch(client):
    files = [("files", ("a.jpg", make_image("clean"), "image/jpeg")),
             ("files", ("b.jpg", make_image("dark"), "image/jpeg"))]
    j = client.post("/api/v1/analyze/batch", files=files).json()
    assert j["analysed"] == 2
    assert j["average_score"] is not None
