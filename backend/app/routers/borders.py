import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Border
from app.schemas import BorderRead, BorderUpdate

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[BorderRead])
def list_borders(db: Session = Depends(get_db)):
    try:
        return db.query(Border).all()
    except Exception as e:
        logger.error(f"Error fetching borders: {e}")
        return []


@router.get("/{border_id}", response_model=BorderRead)
def get_border(border_id: int, db: Session = Depends(get_db)):
    border = db.query(Border).filter(Border.id == border_id).first()
    if not border:
        raise HTTPException(status_code=404, detail="Border not found")
    return border


@router.put("/{border_id}", response_model=BorderRead)
def update_border(
    border_id: int,
    update: BorderUpdate,
    db: Session = Depends(get_db),
):
    border = db.query(Border).filter(Border.id == border_id).first()
    if not border:
        raise HTTPException(status_code=404, detail="Border not found")

    if update.wait_time_min is not None:
        border.wait_time_min = max(0.0, update.wait_time_min)
    if update.inspection_rate is not None:
        border.inspection_rate = max(0.0, min(1.0, update.inspection_rate))
    if update.weather_risk is not None:
        border.weather_risk = max(0.0, min(1.0, update.weather_risk))
    if update.status is not None:
        border.status = update.status

    border.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(border)
    return border
