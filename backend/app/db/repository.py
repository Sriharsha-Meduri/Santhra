"""Data-access layer for analyses (thin, testable functions)."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Analysis


def create(db: Session, record: dict) -> Analysis:
    obj = Analysis(**record)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get(db: Session, analysis_id: str) -> Analysis | None:
    return db.get(Analysis, analysis_id)


def delete(db: Session, analysis_id: str) -> bool:
    obj = db.get(Analysis, analysis_id)
    if obj is None:
        return False
    db.delete(obj)
    db.commit()
    return True


def list_analyses(
    db: Session,
    *,
    limit: int = 20,
    offset: int = 0,
    label: str | None = None,
    search: str | None = None,
    sort: str = "created_at",
    order: str = "desc",
) -> tuple[list[Analysis], int]:
    stmt = select(Analysis)
    count_stmt = select(func.count(Analysis.id))
    if label:
        stmt = stmt.where(Analysis.quality_label == label)
        count_stmt = count_stmt.where(Analysis.quality_label == label)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(Analysis.filename.ilike(like))
        count_stmt = count_stmt.where(Analysis.filename.ilike(like))

    sort_col = {
        "created_at": Analysis.created_at,
        "quality_score": Analysis.quality_score,
        "filename": Analysis.filename,
    }.get(sort, Analysis.created_at)
    sort_col = sort_col.desc() if order == "desc" else sort_col.asc()

    total = db.execute(count_stmt).scalar_one()
    rows = db.execute(stmt.order_by(sort_col).limit(limit).offset(offset)).scalars().all()
    return list(rows), int(total)


def statistics(db: Session) -> dict:
    total = db.execute(select(func.count(Analysis.id))).scalar_one()
    if total == 0:
        return {"total": 0, "average_score": None, "by_label": {}, "review_rate": 0.0}
    avg = db.execute(select(func.avg(Analysis.quality_score))).scalar_one()
    by_label = dict(
        db.execute(
            select(Analysis.quality_label, func.count(Analysis.id)).group_by(Analysis.quality_label)
        ).all()
    )
    reviews = db.execute(
        select(func.count(Analysis.id)).where(Analysis.review_recommended == 1)
    ).scalar_one()
    return {
        "total": int(total),
        "average_score": round(float(avg), 1),
        "by_label": {k: int(v) for k, v in by_label.items()},
        "review_rate": round(reviews / total, 3),
    }
